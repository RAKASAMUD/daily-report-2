"""Tests for signal_engine.store — Task A1."""

import pytest

from data_layer.db import connect
from signal_engine.types import Signal
from signal_engine.store import init_signals_schema, write_signal, get_signals


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn():
    conn = connect(":memory:")
    init_signals_schema(conn)
    return conn


def _make_signal(
    symbol="BTC/USDT",
    timeframe="1h",
    strategy="ema_cross",
    bar_open_time=1_700_000_000_000,
    direction="long",
    entry=30_000.0,
    tp=31_000.0,
    sl=29_500.0,
    rr=2.0,
    reason="EMA20>EMA50 cross",
    created_at=1_700_000_060_000,
) -> Signal:
    return Signal(
        symbol=symbol,
        timeframe=timeframe,
        strategy=strategy,
        bar_open_time=bar_open_time,
        direction=direction,
        entry=entry,
        tp=tp,
        sl=sl,
        rr=rr,
        reason=reason,
        created_at=created_at,
    )


# ---------------------------------------------------------------------------
# Tests: write_signal dedup
# ---------------------------------------------------------------------------

class TestWriteSignal:
    def test_first_insert_returns_one(self):
        """Writing a new signal returns 1."""
        conn = _make_conn()
        sig = _make_signal()
        assert write_signal(conn, sig) == 1

    def test_duplicate_insert_returns_zero(self):
        """Writing the same signal twice returns 0 on the second call."""
        conn = _make_conn()
        sig = _make_signal()
        write_signal(conn, sig)
        assert write_signal(conn, sig) == 0

    def test_duplicate_does_not_increase_table_count(self):
        """Table count stays at 1 after inserting same signal twice."""
        conn = _make_conn()
        sig = _make_signal()
        write_signal(conn, sig)
        write_signal(conn, sig)
        count = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
        assert count == 1

    def test_different_strategy_same_bar_both_insert(self):
        """Two strategies on the same (symbol, tf, bar) both insert — strategy is part of PK."""
        conn = _make_conn()
        sig1 = _make_signal(strategy="ema_cross")
        sig2 = _make_signal(strategy="breakout")
        assert write_signal(conn, sig1) == 1
        assert write_signal(conn, sig2) == 1
        count = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
        assert count == 2

    def test_different_bar_same_strategy_both_insert(self):
        """Same strategy on different bars → both insert."""
        conn = _make_conn()
        sig1 = _make_signal(bar_open_time=1_700_000_000_000)
        sig2 = _make_signal(bar_open_time=1_700_003_600_000)
        assert write_signal(conn, sig1) == 1
        assert write_signal(conn, sig2) == 1


# ---------------------------------------------------------------------------
# Tests: get_signals round-trip + filters
# ---------------------------------------------------------------------------

class TestGetSignals:
    def test_roundtrip_all_fields(self):
        """get_signals returns a Signal with all fields matching what was written."""
        conn = _make_conn()
        sig = _make_signal()
        write_signal(conn, sig)
        results = get_signals(conn)
        assert len(results) == 1
        got = results[0]
        assert got.symbol == sig.symbol
        assert got.timeframe == sig.timeframe
        assert got.strategy == sig.strategy
        assert got.bar_open_time == sig.bar_open_time
        assert got.direction == sig.direction
        assert got.entry == pytest.approx(sig.entry)
        assert got.tp == pytest.approx(sig.tp)
        assert got.sl == pytest.approx(sig.sl)
        assert got.rr == pytest.approx(sig.rr)
        assert got.reason == sig.reason
        assert got.created_at == sig.created_at

    def test_ascending_by_bar_open_time(self):
        """Results are ordered ascending by bar_open_time."""
        conn = _make_conn()
        for i in range(5):
            write_signal(conn, _make_signal(bar_open_time=1_700_000_000_000 + i * 3_600_000))
        results = get_signals(conn, limit=10)
        times = [r.bar_open_time for r in results]
        assert times == sorted(times)

    def test_limit_returns_most_recent(self):
        """limit=N returns the N most recent signals (still ascending in output)."""
        conn = _make_conn()
        for i in range(10):
            write_signal(conn, _make_signal(bar_open_time=1_700_000_000_000 + i * 3_600_000))
        results = get_signals(conn, limit=3)
        assert len(results) == 3
        # Should be the 3 most recent, still ascending
        assert results[0].bar_open_time < results[1].bar_open_time < results[2].bar_open_time
        assert results[-1].bar_open_time == 1_700_000_000_000 + 9 * 3_600_000

    def test_filter_by_symbol(self):
        """Filtering by symbol only returns matching rows."""
        conn = _make_conn()
        write_signal(conn, _make_signal(symbol="BTC/USDT", bar_open_time=1_700_000_000_000))
        write_signal(conn, _make_signal(symbol="ETH/USDT", bar_open_time=1_700_000_000_000, strategy="s2"))
        results = get_signals(conn, symbol="BTC/USDT")
        assert all(r.symbol == "BTC/USDT" for r in results)
        assert len(results) == 1

    def test_filter_by_timeframe(self):
        """Filtering by timeframe only returns matching rows."""
        conn = _make_conn()
        write_signal(conn, _make_signal(timeframe="1h", bar_open_time=1_700_000_000_000))
        write_signal(conn, _make_signal(timeframe="4h", bar_open_time=1_700_000_000_000, strategy="s2"))
        results = get_signals(conn, timeframe="4h")
        assert len(results) == 1
        assert results[0].timeframe == "4h"

    def test_filter_by_strategy(self):
        """Filtering by strategy only returns matching rows."""
        conn = _make_conn()
        write_signal(conn, _make_signal(strategy="ema_cross", bar_open_time=1_700_000_000_000))
        write_signal(conn, _make_signal(strategy="breakout", bar_open_time=1_700_000_000_000, timeframe="4h"))
        results = get_signals(conn, strategy="ema_cross")
        assert len(results) == 1
        assert results[0].strategy == "ema_cross"

    def test_empty_db_returns_empty_list(self):
        """No signals in DB → empty list returned."""
        conn = _make_conn()
        assert get_signals(conn) == []
