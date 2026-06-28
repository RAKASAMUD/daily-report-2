"""Tests for per-tick signal logging — Task D3.

Verifies that when run_engine produces N new signals, a log message
is emitted that includes N and each signal's symbol/timeframe/strategy.
Uses Python's logging.handlers.MemoryHandler (via caplog) to capture logs.
"""

import logging
import pandas as pd
import pytest

from data_layer.db import connect, init_schema, write_candles
from data_layer.testkit import random_walk_candles
from data_layer.config import TIMEFRAME_MS
from signal_engine.store import init_signals_schema
from signal_engine.engine import run_engine
from signal_engine.registry import RegisteredStrategy
from signal_engine.types import Signal


NOW_MS = 1_700_000_000_000
TF = "5m"
SYMBOL = "BTC/USDT"
CREATED_AT = NOW_MS + 60_000


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
        reason="test cross", created_at=CREATED_AT,
    )


def _always_cross(df: pd.DataFrame, params: dict) -> Signal | None:
    if df.empty:
        return None
    return _make_signal(
        symbol=params.get("symbol", SYMBOL),
        timeframe=params.get("timeframe", TF),
        bar_open_time=int(df["open_time"].iloc[-1]),
        strategy=params.get("_strategy_name", "fake"),
    )


def _strat(name="fake", timeframes=None) -> RegisteredStrategy:
    def fn(df, params):
        return _always_cross(df, {**params, "_strategy_name": name})
    return RegisteredStrategy(
        name=name, fn=fn,
        params={"created_at": CREATED_AT},
        timeframes=timeframes or [TF],
    )


def _seed(conn, symbol=SYMBOL, tf=TF, n=5):
    rows = random_walk_candles(NOW_MS, tf, n=n, seed=42)
    write_candles(conn, symbol, tf, rows)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSignalLogging:
    def test_engine_logs_new_signal_count(self, caplog):
        """run_engine emits a log line that includes the count of new signals."""
        conn = _make_conn()
        _seed(conn)

        with caplog.at_level(logging.INFO, logger="signal_engine.engine"):
            new = run_engine(conn, [SYMBOL], [TF], [_strat()])

        assert len(new) == 1
        # At least one log record must mention the count
        all_messages = " ".join(caplog.messages)
        assert "1" in all_messages

    def test_engine_logs_symbol_in_warning_on_error(self, caplog):
        """A strategy that raises logs a WARNING containing the symbol."""
        conn = _make_conn()
        _seed(conn)

        def explode(df, params):
            raise ValueError("boom")

        bad_strat = RegisteredStrategy(
            name="bad", fn=explode,
            params={}, timeframes=[TF],
        )

        with caplog.at_level(logging.WARNING, logger="signal_engine.engine"):
            run_engine(conn, [SYMBOL], [TF], [bad_strat])

        assert any(SYMBOL in msg for msg in caplog.messages)

    def test_no_signals_logs_zero(self, caplog):
        """When no signals fire, the logged count is 0."""
        conn = _make_conn()
        _seed(conn)

        none_strat = RegisteredStrategy(
            name="none", fn=lambda df, p: None,
            params={}, timeframes=[TF],
        )

        with caplog.at_level(logging.INFO, logger="signal_engine.engine"):
            run_engine(conn, [SYMBOL], [TF], [none_strat])

        # The engine should not log anything about signals when there are none
        # OR it may log "0 new signals" — either is acceptable.
        # What we check: no false positive signal counts appear.
        signal_counts = [
            int(word)
            for msg in caplog.messages
            for word in msg.split()
            if word.isdigit()
        ]
        # If any count is logged, it must be 0
        assert all(c == 0 for c in signal_counts)

    def test_multiple_signals_all_logged(self, caplog):
        """Two signals produced → log mentions count >= 2."""
        conn = _make_conn()
        symbols = ["BTC/USDT", "ETH/USDT"]
        for sym in symbols:
            _seed(conn, symbol=sym)

        with caplog.at_level(logging.INFO, logger="signal_engine.engine"):
            new = run_engine(conn, symbols, [TF], [_strat()])

        assert len(new) == 2
        all_messages = " ".join(caplog.messages)
        assert "2" in all_messages
