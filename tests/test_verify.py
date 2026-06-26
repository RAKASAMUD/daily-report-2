"""Tests for scripts/verify — Task E3: on-demand integrity verify tool."""

import pytest

from data_layer.db import connect, init_schema, write_candles
from data_layer.testkit import random_walk_candles, FakeExchange
from data_layer.config import TIMEFRAME_MS
from scripts.verify import verify_pair, verify_all


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn():
    conn = connect(":memory:")
    init_schema(conn)
    return conn


def _rows_to_ccxt(rows):
    return [[r[0], r[1], r[2], r[3], r[4], r[5]] for r in rows]


SYMBOL = "BTC/USDT"
TF = "5m"
TF_MS = TIMEFRAME_MS[TF]


# ---------------------------------------------------------------------------
# Tests: verify_pair
# ---------------------------------------------------------------------------

class TestVerifyPair:
    def test_contiguous_series_reports_zero_gaps(self):
        """A fully contiguous series produces an empty gaps list."""
        conn = _make_conn()
        rows = random_walk_candles(1_700_000_000_000, TF, n=20, seed=10)
        write_candles(conn, SYMBOL, TF, rows)

        report = verify_pair(conn, adapter=None, symbol=SYMBOL, timeframe=TF,
                             now_ms=rows[-1][0] + TF_MS * 2)
        assert report["gaps"] == []
        assert report["gaps_found"] == 0

    def test_series_with_hole_reports_gap(self):
        """A series with a missing candle is reported correctly."""
        conn = _make_conn()
        rows = random_walk_candles(1_700_000_000_000, TF, n=10, seed=11)
        # Remove row 5 to punch a hole
        hole_time = rows[5][0]
        rows_with_hole = rows[:5] + rows[6:]
        write_candles(conn, SYMBOL, TF, rows_with_hole)

        report = verify_pair(conn, adapter=None, symbol=SYMBOL, timeframe=TF,
                             now_ms=rows[-1][0] + TF_MS * 2)
        assert hole_time in report["gaps"]
        assert report["gaps_found"] == 1

    def test_hole_is_filled_after_verify_with_adapter(self):
        """When a gap is found and an adapter is provided, the hole is filled."""
        conn = _make_conn()
        rows = random_walk_candles(1_700_000_000_000, TF, n=10, seed=12)
        hole_row = rows[4]
        rows_with_hole = rows[:4] + rows[5:]
        write_candles(conn, SYMBOL, TF, rows_with_hole)

        # Adapter that returns the missing row
        from data_layer.binance import BinanceAdapter
        now_ms = rows[-1][0] + TF_MS * 2
        fake = FakeExchange(pages=[_rows_to_ccxt([hole_row]), []])
        adapter = BinanceAdapter(fake)

        report = verify_pair(conn, adapter=adapter, symbol=SYMBOL, timeframe=TF,
                             now_ms=now_ms)
        assert report["gaps_found"] == 1
        assert report["filled"] == 1

        # Second run should find zero gaps
        report2 = verify_pair(conn, adapter=None, symbol=SYMBOL, timeframe=TF,
                              now_ms=now_ms)
        assert report2["gaps_found"] == 0

    def test_report_contains_expected_keys(self):
        """verify_pair report always has symbol, timeframe, gaps_found, filled."""
        conn = _make_conn()
        rows = random_walk_candles(1_700_000_000_000, TF, n=5, seed=13)
        write_candles(conn, SYMBOL, TF, rows)

        report = verify_pair(conn, adapter=None, symbol=SYMBOL, timeframe=TF,
                             now_ms=rows[-1][0] + TF_MS * 2)
        for key in ("symbol", "timeframe", "gaps", "gaps_found", "filled"):
            assert key in report


# ---------------------------------------------------------------------------
# Tests: verify_all
# ---------------------------------------------------------------------------

class TestVerifyAll:
    def test_verify_all_returns_report_per_pair(self):
        """verify_all returns one report per (symbol, timeframe) pair."""
        conn = _make_conn()
        symbols = ["BTC/USDT", "ETH/USDT"]
        timeframes = ["5m", "15m"]

        for sym in symbols:
            for tf in timeframes:
                rows = random_walk_candles(1_700_000_000_000, tf, n=5, seed=99)
                write_candles(conn, sym, tf, rows)

        now_ms = 1_700_000_000_000 + TIMEFRAME_MS["15m"] * 10
        reports = verify_all(conn, adapter=None, symbols=symbols,
                             timeframes=timeframes, now_ms=now_ms)

        assert len(reports) == len(symbols) * len(timeframes)
        for sym in symbols:
            for tf in timeframes:
                assert any(
                    r["symbol"] == sym and r["timeframe"] == tf
                    for r in reports
                )

    def test_verify_all_empty_db_returns_reports(self):
        """verify_all on empty DB returns reports with 0 gaps (nothing to check)."""
        conn = _make_conn()
        now_ms = 1_700_000_000_000
        reports = verify_all(conn, adapter=None,
                             symbols=["BTC/USDT"], timeframes=["5m"],
                             now_ms=now_ms)
        assert len(reports) == 1
        assert reports[0]["gaps_found"] == 0
