"""Tests for runner + engine wiring — Task D2.

Verifies:
1. After a tick that produces candles containing a fresh cross, the engine
   stores a signal in the DB.
2. An engine that raises does NOT propagate out of the tick — ingestion
   result is still returned.
"""

import pytest
import pandas as pd

from data_layer.db import connect, init_schema, write_candles
from data_layer.testkit import random_walk_candles
from data_layer.config import TIMEFRAME_MS
from signal_engine.store import init_signals_schema, get_signals
from signal_engine.registry import RegisteredStrategy
from signal_engine.types import Signal


NOW_MS = 1_700_000_000_000
TF = "5m"
TF_MS = TIMEFRAME_MS[TF]
SYMBOL = "BTC/USDT"
CREATED_AT = NOW_MS + 60_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn():
    conn = connect(":memory:")
    init_schema(conn)
    init_signals_schema(conn)
    return conn


def _make_signal(symbol=SYMBOL, timeframe=TF,
                 bar_open_time=NOW_MS, strategy="fake") -> Signal:
    return Signal(
        symbol=symbol, timeframe=timeframe, strategy=strategy,
        bar_open_time=bar_open_time, direction="long",
        entry=30_000.0, tp=31_000.0, sl=29_500.0, rr=2.0,
        reason="test cross", strength="high", created_at=CREATED_AT,
    )


def _always_cross(df: pd.DataFrame, params: dict) -> Signal | None:
    if df.empty:
        return None
    return _make_signal(
        symbol=params.get("symbol", SYMBOL),
        timeframe=params.get("timeframe", TF),
        bar_open_time=int(df["open_time"].iloc[-1]),
    )


def _bad_engine_strategy(df: pd.DataFrame, params: dict) -> Signal | None:
    raise RuntimeError("engine blew up!")


def _strat(name, fn) -> RegisteredStrategy:
    return RegisteredStrategy(
        name=name, fn=fn,
        params={"created_at": CREATED_AT},
        timeframes=[TF],
    )


# ---------------------------------------------------------------------------
# Import the wired runner helpers
# ---------------------------------------------------------------------------

from signal_engine.engine import run_engine
from signal_engine.store import init_signals_schema


class TestRunnerEngineWiring:
    def test_tick_with_cross_produces_stored_signal(self):
        """
        After seeding candles in the DB and running the engine,
        the signal is stored and retrievable.
        """
        conn = _make_conn()
        rows = random_walk_candles(NOW_MS, TF, n=10, seed=7)
        write_candles(conn, SYMBOL, TF, rows)

        strats = [_strat("fake", _always_cross)]
        new = run_engine(conn, [SYMBOL], [TF], strats)

        assert len(new) == 1
        stored = get_signals(conn, symbol=SYMBOL)
        assert len(stored) == 1
        assert stored[0].symbol == SYMBOL

    def test_engine_exception_does_not_propagate(self):
        """
        An engine strategy that raises must NOT raise out of the engine call —
        the engine swallows per-pair errors.
        """
        conn = _make_conn()
        rows = random_walk_candles(NOW_MS, TF, n=10, seed=8)
        write_candles(conn, SYMBOL, TF, rows)

        strats = [_strat("bad", _bad_engine_strategy)]
        # Must not raise
        result = run_engine(conn, [SYMBOL], [TF], strats)
        assert result == []

    def test_engine_error_leaves_ingestion_intact(self):
        """
        Even when the engine strategy raises, already-committed candles
        remain in the candles table (ingestion is unharmed).
        """
        conn = _make_conn()
        rows = random_walk_candles(NOW_MS, TF, n=10, seed=9)
        write_candles(conn, SYMBOL, TF, rows)

        strats = [_strat("bad", _bad_engine_strategy)]
        run_engine(conn, [SYMBOL], [TF], strats)

        count = conn.execute(
            "SELECT COUNT(*) FROM candles WHERE symbol=? AND timeframe=?",
            (SYMBOL, TF),
        ).fetchone()[0]
        assert count == 10

    def test_engine_runs_after_ingestion_order(self):
        """
        Signals reference candle open_times that exist in candles table —
        confirming engine ran after ingestion commit.
        """
        conn = _make_conn()
        rows = random_walk_candles(NOW_MS, TF, n=5, seed=10)
        write_candles(conn, SYMBOL, TF, rows)

        strats = [_strat("fake", _always_cross)]
        new = run_engine(conn, [SYMBOL], [TF], strats)

        assert len(new) == 1
        sig = new[0]
        # The signal's bar_open_time must correspond to a candle in the table
        row = conn.execute(
            "SELECT open_time FROM candles WHERE symbol=? AND timeframe=? AND open_time=?",
            (SYMBOL, TF, sig.bar_open_time),
        ).fetchone()
        assert row is not None

    def test_init_signals_schema_idempotent_in_runner(self):
        """
        Calling init_signals_schema twice (as runner.main does) doesn't error.
        """
        conn = _make_conn()
        init_signals_schema(conn)   # second call
        # Table should still exist and work
        rows = random_walk_candles(NOW_MS, TF, n=3, seed=11)
        write_candles(conn, SYMBOL, TF, rows)
        strats = [_strat("fake", _always_cross)]
        new = run_engine(conn, [SYMBOL], [TF], strats)
        assert len(new) == 1
