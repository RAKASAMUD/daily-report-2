"""Tests for signal_engine.engine — Task D1.

All tests use in-memory SQLite + crafted candle fixtures.
No network access.

Strategy fixture: a tiny "always_cross" strategy that always returns a Signal
so we can control exactly when signals are produced, independent of EMA math.
"""

import time
import pytest
import pandas as pd

from data_layer.db import connect, init_schema, write_candles
from signal_engine.store import init_signals_schema, get_signals
from signal_engine.engine import run_engine
from signal_engine.registry import RegisteredStrategy
from signal_engine.types import Signal
from data_layer.testkit import random_walk_candles
from data_layer.config import TIMEFRAME_MS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn():
    conn = connect(":memory:")
    init_schema(conn)
    init_signals_schema(conn)
    return conn


SYMBOL = "BTC/USDT"
TF = "5m"
TF_MS = TIMEFRAME_MS[TF]
NOW_MS = 1_700_000_000_000
CREATED_AT = NOW_MS + 60_000


def _make_signal(symbol=SYMBOL, timeframe=TF,
                 bar_open_time=NOW_MS) -> Signal:
    return Signal(
        symbol=symbol, timeframe=timeframe, strategy="fake_strat",
        bar_open_time=bar_open_time, direction="long",
        entry=30_000.0, tp=31_000.0, sl=29_500.0, rr=2.0,
        reason="test cross", strength="high", created_at=CREATED_AT,
    )


# Strategy that ALWAYS returns a Signal (deterministic cross)
def _always_cross(df: pd.DataFrame, params: dict) -> Signal | None:
    if df.empty:
        return None
    symbol = params.get("symbol", SYMBOL)
    timeframe = params.get("timeframe", TF)
    return _make_signal(symbol=symbol, timeframe=timeframe,
                        bar_open_time=int(df["open_time"].iloc[-1]))


# Strategy that ALWAYS returns None (no signal)
def _never_cross(df: pd.DataFrame, params: dict) -> Signal | None:
    return None


# Strategy that RAISES an exception
def _bad_strategy(df: pd.DataFrame, params: dict) -> Signal | None:
    raise RuntimeError("strategy exploded!")


def _strat(name: str, fn, timeframes=None) -> RegisteredStrategy:
    return RegisteredStrategy(
        name=name,
        fn=fn,
        params={"created_at": CREATED_AT},
        timeframes=timeframes or [TF],
    )


def _seed_candles(conn, symbol=SYMBOL, tf=TF, n=10) -> list:
    rows = random_walk_candles(NOW_MS, tf, n=n, seed=42)
    write_candles(conn, symbol, tf, rows)
    return rows


# ---------------------------------------------------------------------------
# Tests: basic signal production
# ---------------------------------------------------------------------------

class TestRunEngine:
    def test_fresh_cross_signal_inserted_and_returned(self):
        """
        A pair whose last bar triggers a cross → signal inserted in DB
        and present in the returned list.
        """
        conn = _make_conn()
        rows = _seed_candles(conn)
        strats = [_strat("fake_strat", _always_cross)]

        new = run_engine(conn, [SYMBOL], [TF], strats)

        assert len(new) == 1
        assert new[0].symbol == SYMBOL
        assert new[0].timeframe == TF
        # Verify it was persisted
        stored = get_signals(conn, symbol=SYMBOL)
        assert len(stored) == 1

    def test_idempotent_second_run_returns_empty(self):
        """
        Running engine twice on unchanged data → second run returns []
        (INSERT OR IGNORE dedup).
        """
        conn = _make_conn()
        _seed_candles(conn)
        strats = [_strat("fake_strat", _always_cross)]

        run_engine(conn, [SYMBOL], [TF], strats)
        second = run_engine(conn, [SYMBOL], [TF], strats)

        assert second == []
        # DB still has exactly 1 row
        assert len(get_signals(conn)) == 1

    def test_no_signal_strategy_returns_empty(self):
        """A strategy that always returns None → run_engine returns []."""
        conn = _make_conn()
        _seed_candles(conn)
        strats = [_strat("never", _never_cross)]

        new = run_engine(conn, [SYMBOL], [TF], strats)
        assert new == []
        assert get_signals(conn) == []

    def test_empty_symbols_returns_empty(self):
        conn = _make_conn()
        strats = [_strat("fake_strat", _always_cross)]
        new = run_engine(conn, [], [TF], strats)
        assert new == []

    def test_empty_strategies_returns_empty(self):
        conn = _make_conn()
        _seed_candles(conn)
        new = run_engine(conn, [SYMBOL], [TF], [])
        assert new == []


# ---------------------------------------------------------------------------
# Tests: error isolation
# ---------------------------------------------------------------------------

class TestRunEngineIsolation:
    def test_bad_strategy_does_not_stop_good_strategy(self):
        """
        If one strategy raises, the engine catches it and continues;
        other strategies still produce their signals.
        """
        conn = _make_conn()
        _seed_candles(conn)
        strats = [
            _strat("bad", _bad_strategy),
            _strat("good", _always_cross),
        ]
        new = run_engine(conn, [SYMBOL], [TF], strats)
        # The good strategy must still fire
        assert any(s.strategy == "fake_strat" for s in new)

    def test_bad_pair_does_not_stop_good_pair(self):
        """
        A pair with no candles in DB (get_candles returns empty df) → the
        strategy returns None, and other pairs are unaffected.
        """
        conn = _make_conn()
        # Only seed ETH — BTC has no candles
        _seed_candles(conn, symbol="ETH/USDT")
        strats = [_strat("fake_strat", _always_cross, timeframes=["5m"])]

        new = run_engine(conn, ["BTC/USDT", "ETH/USDT"], [TF], strats)
        # ETH should still produce a signal
        assert any(s.symbol == "ETH/USDT" for s in new)

    def test_strategy_only_runs_on_matching_timeframes(self):
        """
        A strategy registered for ['1h'] only runs on 1h, not 5m.
        """
        conn = _make_conn()
        rows_5m = random_walk_candles(NOW_MS, "5m", n=10, seed=1)
        rows_1h = random_walk_candles(NOW_MS, "1h", n=10, seed=2)
        write_candles(conn, SYMBOL, "5m", rows_5m)
        write_candles(conn, SYMBOL, "1h", rows_1h)

        strat_1h_only = _strat("fake_strat", _always_cross, timeframes=["1h"])
        new = run_engine(conn, [SYMBOL], ["5m", "1h"], [strat_1h_only])

        # Signal only on 1h
        assert all(s.timeframe == "1h" for s in new)
        assert len(new) == 1


# ---------------------------------------------------------------------------
# Tests: multiple pairs / strategies
# ---------------------------------------------------------------------------

class TestRunEngineMultiple:
    def test_multiple_symbols_each_produce_signal(self):
        """Engine iterates all symbols and produces one signal each."""
        conn = _make_conn()
        symbols = ["BTC/USDT", "ETH/USDT"]
        for sym in symbols:
            _seed_candles(conn, symbol=sym)
        strats = [_strat("fake_strat", _always_cross)]

        new = run_engine(conn, symbols, [TF], strats)
        produced_symbols = {s.symbol for s in new}
        assert produced_symbols == set(symbols)

    def test_multiple_strategies_each_produce_signal(self):
        """Two strategies on the same pair both insert (different strategy name in PK)."""
        conn = _make_conn()
        _seed_candles(conn)

        def make_named(name):
            def fn(df, params):
                s = _always_cross(df, params)
                if s:
                    return Signal(
                        symbol=s.symbol, timeframe=s.timeframe,
                        strategy=name,
                        bar_open_time=s.bar_open_time,
                        direction=s.direction,
                        entry=s.entry, tp=s.tp, sl=s.sl, rr=s.rr,
                        reason=s.reason, strength=s.strength, created_at=s.created_at,
                    )
            return fn

        strats = [
            _strat("strat_a", make_named("strat_a")),
            _strat("strat_b", make_named("strat_b")),
        ]
        new = run_engine(conn, [SYMBOL], [TF], strats)
        assert len(new) == 2
        assert len(get_signals(conn)) == 2
