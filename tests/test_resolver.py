"""Tests for tracking.resolver — Task C1."""

import pytest
import pandas as pd

from data_layer.db import connect, init_schema, write_candles
from signal_engine.store import init_signals_schema, write_signal
from signal_engine.types import Signal
from tracking.store import init_outcomes_schema, get_pending_signals, get_outcome_rows
from tracking.resolver import run_resolver

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TF = "1h"
TF_MS = 3_600_000
FIVEMIN_MS = 5 * 60 * 1_000
NOW_MS = 1_000 * TF_MS
BAR_OPEN_TIME = NOW_MS - 5 * TF_MS   # signal 5 bars in the past


def _make_conn():
    conn = connect(":memory:")
    init_schema(conn)
    init_signals_schema(conn)
    init_outcomes_schema(conn)
    return conn


def _make_signal(symbol="BTC/USDT", bar_open_time=BAR_OPEN_TIME) -> Signal:
    return Signal(
        symbol=symbol, timeframe=TF, strategy="ema_cross",
        bar_open_time=bar_open_time, direction="long",
        entry=100.0, tp=110.0, sl=90.0, rr=2.0,
        reason="cross", strength="high",
        created_at=bar_open_time + 60_000,
    )


def _seed_tp_hit_candles(conn, symbol="BTC/USDT"):
    """Write 5m candles that will hit TP (high >= 110) shortly after entry."""
    entry_time = BAR_OPEN_TIME + TF_MS
    rows = []
    t = entry_time
    # First few bars: normal, then TP hit
    for i in range(3):
        rows.append((t + i * FIVEMIN_MS, 100.0, 105.0, 99.0, 102.0, 1.0))
    # TP hit bar
    rows.append((t + 3 * FIVEMIN_MS, 102.0, 111.0, 101.0, 110.0, 1.0))
    # A few more bars to ensure coverage
    for i in range(4, 8):
        rows.append((t + i * FIVEMIN_MS, 102.0, 108.0, 99.0, 103.0, 1.0))
    write_candles(conn, symbol, "5m", [r[:6] for r in rows])


def _seed_young_signal_candles(conn, symbol="BTC/USDT", bar_open_time=None):
    """Write only a couple of 5m bars — window not elapsed, no hit."""
    if bar_open_time is None:
        bar_open_time = NOW_MS - TF_MS  # signal is very recent
    entry_time = bar_open_time + TF_MS
    rows = [
        (entry_time, 100.0, 104.0, 98.0, 102.0, 1.0),
        (entry_time + FIVEMIN_MS, 102.0, 105.0, 99.0, 103.0, 1.0),
    ]
    write_candles(conn, symbol, "5m", rows)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRunResolver:
    def test_tp_hit_resolves_signal(self):
        conn = _make_conn()
        write_signal(conn, _make_signal())
        _seed_tp_hit_candles(conn)

        stats = run_resolver(conn, now_ms=NOW_MS + TF_MS, timeout_bars=10)

        assert stats["resolved"] == 1
        assert stats["failed"] == 0
        assert len(get_pending_signals(conn)) == 0

    def test_young_signal_stays_pending(self):
        """Signal whose window has not elapsed stays pending, no outcome row."""
        conn = _make_conn()
        bar_open_time = NOW_MS - TF_MS  # only 1 bar old
        sig = _make_signal(bar_open_time=bar_open_time)
        write_signal(conn, sig)
        _seed_young_signal_candles(conn, bar_open_time=bar_open_time)

        stats = run_resolver(conn, now_ms=NOW_MS, timeout_bars=10)

        assert stats["resolved"] == 0
        assert stats["pending"] == 1
        assert len(get_pending_signals(conn)) == 1

    def test_idempotent_reruns_resolve_zero(self):
        """Re-running after resolution → resolved=0."""
        conn = _make_conn()
        write_signal(conn, _make_signal())
        _seed_tp_hit_candles(conn)

        run_resolver(conn, now_ms=NOW_MS + TF_MS, timeout_bars=10)
        stats2 = run_resolver(conn, now_ms=NOW_MS + TF_MS, timeout_bars=10)

        assert stats2["resolved"] == 0
        assert stats2["pending"] == 0

    def test_bad_signal_isolated_others_still_resolve(self, monkeypatch):
        """One signal raising in resolve() → logged, others still processed."""
        conn = _make_conn()
        write_signal(conn, _make_signal("BTC/USDT"))
        write_signal(conn, _make_signal("ETH/USDT"))
        _seed_tp_hit_candles(conn, "BTC/USDT")
        _seed_tp_hit_candles(conn, "ETH/USDT")

        call_count = {"n": 0}
        original_resolve = __import__(
            "tracking.resolve", fromlist=["resolve"]
        ).resolve

        def flaky_resolve(sig, candles, timeout_bars):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("Simulated resolve crash")
            return original_resolve(sig, candles, timeout_bars)

        monkeypatch.setattr("tracking.resolver.resolve", flaky_resolve)

        stats = run_resolver(conn, now_ms=NOW_MS + TF_MS, timeout_bars=10)

        # One failed, one resolved
        assert stats["failed"] == 1
        assert stats["resolved"] == 1
