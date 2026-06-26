"""Tests for data_layer.runner — Task D2: tick runner."""

import pytest
from datetime import datetime, timezone

from data_layer.db import connect, init_schema
from data_layer.binance import BinanceAdapter
from data_layer.runner import floor_to_5min, run_tick
from data_layer.testkit import FakeExchange, random_walk_candles
from data_layer.config import TIMEFRAME_MS, SYMBOLS, TIMEFRAMES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def utc_ms(year, month, day, hour=0, minute=0, second=0) -> int:
    dt = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _make_conn():
    conn = connect(":memory:")
    init_schema(conn)
    return conn


def _make_ccxt_rows(n: int, start_ms: int, tf: str) -> list[list]:
    rows = random_walk_candles(start_ms, tf, n, seed=99)
    return [[r[0], r[1], r[2], r[3], r[4], r[5]] for r in rows]


# ---------------------------------------------------------------------------
# Tests: floor_to_5min
# ---------------------------------------------------------------------------

class TestFloorTo5min:
    def test_already_on_boundary_unchanged(self):
        now = utc_ms(2024, 1, 1, hour=4, minute=0)
        assert floor_to_5min(now) == now

    def test_rounds_down_to_nearest_5min(self):
        # 04:03:00 → 04:00:00
        now   = utc_ms(2024, 1, 1, hour=4, minute=3)
        floored = utc_ms(2024, 1, 1, hour=4, minute=0)
        assert floor_to_5min(now) == floored

    def test_rounds_down_at_59s(self):
        # 04:04:59 → 04:00:00
        now     = utc_ms(2024, 1, 1, hour=4, minute=4, second=59)
        floored = utc_ms(2024, 1, 1, hour=4, minute=0)
        assert floor_to_5min(now) == floored

    def test_rounds_down_mid_interval(self):
        # 04:07:30 → 04:05:00
        now     = utc_ms(2024, 1, 1, hour=4, minute=7, second=30)
        floored = utc_ms(2024, 1, 1, hour=4, minute=5)
        assert floor_to_5min(now) == floored


# ---------------------------------------------------------------------------
# Tests: run_tick
# ---------------------------------------------------------------------------

class TestRunTick:
    def _make_adapter(self, symbols, timeframes, now_ms):
        """Build a FakeExchange that returns a few rows for every pair."""
        pages = {}
        for sym in symbols:
            for tf in timeframes:
                start = now_ms - TIMEFRAME_MS[tf] * 5
                rows = _make_ccxt_rows(3, start, tf)
                pages[(sym, tf)] = rows

        class MultiPairFake:
            def __init__(self):
                self._calls = {}

            def fetch_ohlcv(self, symbol, timeframe, since=None, limit=1000):
                key = (symbol, timeframe)
                if key not in self._calls:
                    self._calls[key] = 0
                call_idx = self._calls[key]
                self._calls[key] += 1
                if call_idx == 0:
                    return pages.get(key, [])
                return []  # second call → empty → stop pagination

        return BinanceAdapter(MultiPairFake())

    def test_4h_boundary_processes_all_timeframes(self):
        """At a 4h boundary, all 4 timeframes are processed for every symbol."""
        conn = _make_conn()
        now_ms = utc_ms(2024, 1, 1, hour=4)  # 4h boundary
        symbols = ["BTC/USDT", "ETH/USDT"]
        timeframes = ["5m", "15m", "1h", "4h"]

        adapter = self._make_adapter(symbols, timeframes, now_ms)
        summary = run_tick(conn, adapter, now_ms, symbols, timeframes, backfill_days=1)

        # All 8 pairs (2 symbols × 4 timeframes) should be in the summary
        assert len(summary) == 8
        for sym in symbols:
            for tf in timeframes:
                assert (sym, tf) in summary

    def test_5m_only_boundary_processes_only_5m(self):
        """At a 5m-only boundary, only the 5m timeframe is processed."""
        conn = _make_conn()
        now_ms = utc_ms(2024, 1, 1, hour=4, minute=5)  # 5m only
        symbols = ["BTC/USDT"]
        timeframes = ["5m", "15m", "1h", "4h"]

        adapter = self._make_adapter(symbols, timeframes, now_ms)
        summary = run_tick(conn, adapter, now_ms, symbols, timeframes, backfill_days=1)

        # Only ("BTC/USDT", "5m") should appear
        assert set(summary.keys()) == {("BTC/USDT", "5m")}

    def test_error_in_one_pair_does_not_stop_others(self):
        """One pair raising an exception is logged and loop continues; others succeed."""
        conn = _make_conn()
        now_ms = utc_ms(2024, 1, 1, hour=4)  # 4h boundary → all tfs due
        symbols = ["BTC/USDT", "ETH/USDT"]
        timeframes = ["5m", "15m", "1h", "4h"]

        class ErrorOnBtc5m:
            """Always errors for BTC/USDT 5m; returns rows otherwise."""
            def __init__(self):
                self._calls = {}

            def fetch_ohlcv(self, symbol, timeframe, since=None, limit=1000):
                if symbol == "BTC/USDT" and timeframe == "5m":
                    raise RuntimeError("simulated network error")
                key = (symbol, timeframe)
                idx = self._calls.get(key, 0)
                self._calls[key] = idx + 1
                if idx == 0:
                    start = now_ms - TIMEFRAME_MS[timeframe] * 5
                    rows = random_walk_candles(start, timeframe, 3, seed=77)
                    return [[r[0], r[1], r[2], r[3], r[4], r[5]] for r in rows]
                return []

        adapter = BinanceAdapter(ErrorOnBtc5m())
        summary = run_tick(conn, adapter, now_ms, symbols, timeframes, backfill_days=1)

        # BTC/USDT 5m should have an error recorded
        btc5m = summary[("BTC/USDT", "5m")]
        assert isinstance(btc5m, Exception)

        # All other 7 pairs should have succeeded (integer inserted count)
        for sym in symbols:
            for tf in timeframes:
                if (sym, tf) == ("BTC/USDT", "5m"):
                    continue
                assert isinstance(summary[(sym, tf)], int), \
                    f"Expected int for {sym}/{tf}, got {summary[(sym, tf)]}"

    def test_summary_keys_are_symbol_tf_tuples(self):
        """summary dict keys are (symbol, timeframe) tuples."""
        conn = _make_conn()
        now_ms = utc_ms(2024, 1, 1, hour=4, minute=5)  # 5m only
        symbols = ["BTC/USDT"]
        timeframes = ["5m", "15m", "1h", "4h"]

        adapter = self._make_adapter(symbols, timeframes, now_ms)
        summary = run_tick(conn, adapter, now_ms, symbols, timeframes, backfill_days=1)

        for key in summary:
            assert isinstance(key, tuple) and len(key) == 2

    def test_no_due_timeframes_returns_empty_summary(self):
        """
        When no timeframe is due (e.g. now is a 5m boundary but the
        timeframes list only contains 1h and 4h), the summary is empty.
        """
        conn = _make_conn()
        # 04:05:00 is a 5m boundary but NOT a 15m, 1h, or 4h boundary
        now_ms = utc_ms(2024, 1, 1, hour=4, minute=5)
        symbols = ["BTC/USDT"]
        # Only watch 1h and 4h — neither is due at 04:05
        timeframes = ["1h", "4h"]

        adapter = self._make_adapter(symbols, ["5m", "15m", "1h", "4h"], now_ms)
        summary = run_tick(conn, adapter, now_ms, symbols, timeframes, backfill_days=1)

        assert summary == {}

