"""Tests for outcomes store + get_candles_since — Task A1."""

import pytest
import time

from data_layer.db import connect, init_schema, write_candles, get_candles_since
from signal_engine.store import init_signals_schema, write_signal
from signal_engine.types import Signal
from tracking.store import (
    init_outcomes_schema,
    write_outcome,
    get_pending_signals,
    get_outcome_rows,
)
from tracking.types import Outcome

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW_MS = 1_700_000_000_000
SIG_BOT = NOW_MS  # bar_open_time


def _make_conn():
    conn = connect(":memory:")
    init_schema(conn)
    init_signals_schema(conn)
    init_outcomes_schema(conn)
    return conn


def _make_signal(symbol="BTC/USDT", bar_open_time=SIG_BOT, strategy="ema_cross") -> Signal:
    return Signal(
        symbol=symbol, timeframe="1h", strategy=strategy,
        bar_open_time=bar_open_time, direction="long",
        entry=100.0, tp=110.0, sl=95.0, rr=2.0,
        reason="cross", strength="high", created_at=bar_open_time + 60_000,
    )


def _make_outcome(symbol="BTC/USDT", bar_open_time=SIG_BOT, status="win") -> Outcome:
    return Outcome(
        symbol=symbol, timeframe="1h", strategy="ema_cross",
        bar_open_time=bar_open_time, status=status,
        realized_r=2.0 if status == "win" else -1.0,
        bars_to_resolution=3,
        resolved_at=bar_open_time + 3 * 3_600_000,
        resolution_price=110.0 if status == "win" else 95.0,
    )


# ---------------------------------------------------------------------------
# Tests: outcomes store
# ---------------------------------------------------------------------------

class TestOutcomesStore:
    def test_signal_with_no_outcome_is_pending(self):
        conn = _make_conn()
        write_signal(conn, _make_signal())

        pending = get_pending_signals(conn)
        assert len(pending) == 1
        assert pending[0].symbol == "BTC/USDT"

    def test_write_outcome_removes_from_pending(self):
        conn = _make_conn()
        sig = _make_signal()
        write_signal(conn, sig)
        assert len(get_pending_signals(conn)) == 1

        write_outcome(conn, _make_outcome())
        assert len(get_pending_signals(conn)) == 0

    def test_write_outcome_returns_1_on_insert_0_on_dup(self):
        conn = _make_conn()
        write_signal(conn, _make_signal())

        o = _make_outcome()
        assert write_outcome(conn, o) == 1
        assert write_outcome(conn, o) == 0  # duplicate

    def test_multiple_pending_signals_all_returned(self):
        conn = _make_conn()
        write_signal(conn, _make_signal("BTC/USDT", SIG_BOT))
        write_signal(conn, _make_signal("ETH/USDT", SIG_BOT))

        pending = get_pending_signals(conn)
        assert len(pending) == 2

    def test_get_outcome_rows_returns_correct_tuples(self):
        conn = _make_conn()
        write_signal(conn, _make_signal())
        write_outcome(conn, _make_outcome(status="win"))

        rows = get_outcome_rows(conn)
        assert len(rows) == 1
        strategy, timeframe, status, realized_r = rows[0]
        assert strategy == "ema_cross"
        assert timeframe == "1h"
        assert status == "win"
        assert realized_r == 2.0


# ---------------------------------------------------------------------------
# Tests: get_candles_since
# ---------------------------------------------------------------------------

class TestGetCandlesSince:
    def test_returns_only_candles_at_or_after_cutoff(self):
        conn = connect(":memory:")
        init_schema(conn)

        rows = [
            (1000, 1.0, 1.1, 0.9, 1.05, 100.0),
            (2000, 1.1, 1.2, 1.0, 1.15, 110.0),
            (3000, 1.2, 1.3, 1.1, 1.25, 120.0),
        ]
        write_candles(conn, "BTC/USDT", "5m", rows)

        df = get_candles_since(conn, "BTC/USDT", "5m", since_ms=2000)
        assert len(df) == 2
        assert df["open_time"].iloc[0] == 2000
        assert df["open_time"].iloc[1] == 3000

    def test_ascending_order(self):
        conn = connect(":memory:")
        init_schema(conn)

        rows = [
            (3000, 1.0, 1.1, 0.9, 1.0, 10.0),
            (1000, 1.0, 1.1, 0.9, 1.0, 10.0),
            (2000, 1.0, 1.1, 0.9, 1.0, 10.0),
        ]
        write_candles(conn, "BTC/USDT", "5m", rows)

        df = get_candles_since(conn, "BTC/USDT", "5m", since_ms=1000)
        assert list(df["open_time"]) == [1000, 2000, 3000]

    def test_empty_result_when_all_before_cutoff(self):
        conn = connect(":memory:")
        init_schema(conn)
        write_candles(conn, "BTC/USDT", "5m", [(500, 1.0, 1.1, 0.9, 1.0, 10.0)])

        df = get_candles_since(conn, "BTC/USDT", "5m", since_ms=1000)
        assert df.empty
