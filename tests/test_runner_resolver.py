"""Tests for resolver wiring in the tick — Task C2."""

import logging
import pytest
import pandas as pd

from data_layer.db import connect, init_schema, write_candles
from signal_engine.store import init_signals_schema, write_signal
from signal_engine.types import Signal
from tracking.store import init_outcomes_schema, get_pending_signals
from data_layer.runner import run_resolver_step

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TF_MS = 3_600_000
FIVEMIN_MS = 5 * 60 * 1_000
BAR_OPEN_TIME = 5 * TF_MS


def _make_conn():
    conn = connect(":memory:")
    init_schema(conn)
    init_signals_schema(conn)
    init_outcomes_schema(conn)
    return conn


def _make_signal(symbol="BTC/USDT") -> Signal:
    return Signal(
        symbol=symbol, timeframe="1h", strategy="ema_cross",
        bar_open_time=BAR_OPEN_TIME, direction="long",
        entry=100.0, tp=110.0, sl=90.0, rr=2.0,
        reason="cross", strength="high",
        created_at=BAR_OPEN_TIME + 60_000,
    )


def _seed_tp_hit(conn, symbol="BTC/USDT"):
    entry_time = BAR_OPEN_TIME + TF_MS
    rows = []
    for i in range(4):
        rows.append((entry_time + i * FIVEMIN_MS, 100.0, 105.0, 99.0, 102.0, 1.0))
    # TP hit
    rows.append((entry_time + 4 * FIVEMIN_MS, 100.0, 111.0, 99.0, 110.0, 1.0))
    # extra coverage
    for i in range(5, 10):
        rows.append((entry_time + i * FIVEMIN_MS, 100.0, 108.0, 99.0, 104.0, 1.0))
    write_candles(conn, symbol, "5m", rows)


class TestRunnerResolver:
    def test_run_resolver_step_resolves_ready_signal(self):
        conn = _make_conn()
        write_signal(conn, _make_signal())
        _seed_tp_hit(conn)

        now_ms = BAR_OPEN_TIME + 15 * TF_MS  # well past timeout window
        run_resolver_step(conn, now_ms=now_ms)

        assert len(get_pending_signals(conn)) == 0

    def test_run_resolver_step_exception_is_swallowed(self, caplog, monkeypatch):
        """An exception inside run_resolver does not propagate out of the tick."""
        conn = _make_conn()

        def fake_run_resolver(*args, **kwargs):
            raise RuntimeError("Resolver exploded")

        monkeypatch.setattr("data_layer.runner.run_resolver", fake_run_resolver)

        with caplog.at_level(logging.ERROR, logger="data_layer.runner"):
            # Should not raise
            run_resolver_step(conn, now_ms=99999)

        assert any("resolver error" in msg for msg in caplog.messages)
