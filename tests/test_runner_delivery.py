"""Tests for delivery wiring — Task D1."""

import logging
import pytest

from data_layer.db import connect
from signal_engine.store import init_signals_schema, write_signal, get_undelivered, migrate_signals_schema
from signal_engine.types import Signal
from data_layer.runner import run_delivery_step


def _make_conn():
    conn = connect(":memory:")
    init_signals_schema(conn)
    migrate_signals_schema(conn)
    return conn


def _make_signal(symbol="BTC/USDT", created_at=1000) -> Signal:
    return Signal(
        symbol=symbol, timeframe="1h", strategy="ema_cross",
        bar_open_time=created_at - 100, direction="long",
        entry=1.0, tp=2.0, sl=0.5, rr=2.0,
        reason="test", strength="high", created_at=created_at,
    )


class FakeNotifier:
    def __init__(self, should_raise=False):
        self.sent = []
        self.should_raise = should_raise

    def send(self, message: str) -> bool:
        if self.should_raise:
            raise RuntimeError("Notifier exploded")
        self.sent.append(message)
        return True


class TestRunnerDelivery:
    def test_run_delivery_step_sends_and_marks(self):
        """A tick delivers an undelivered signal and marks it."""
        conn = _make_conn()
        write_signal(conn, _make_signal("S1"))
        
        notifier = FakeNotifier()
        run_delivery_step(conn, now_ms=9999, notifier=notifier)
        
        assert len(notifier.sent) == 1
        assert "S1" in notifier.sent[0]
        
        # Verify it was marked
        assert len(get_undelivered(conn, 10)) == 0
        
        # Verify sent_at was set
        row = conn.execute("SELECT sent_at FROM signals").fetchone()
        assert row[0] == 9999

    def test_run_delivery_step_exception_is_swallowed(self, caplog, monkeypatch):
        """A failure in the delivery driver does not propagate out of the tick."""
        conn = _make_conn()
        
        def fake_deliver(*args, **kwargs):
            raise RuntimeError("Database exploded")
            
        monkeypatch.setattr("data_layer.runner.deliver_pending", fake_deliver)
        
        with caplog.at_level(logging.ERROR, logger="data_layer.runner"):
            # Should not raise
            run_delivery_step(conn, now_ms=9999, notifier=FakeNotifier())
            
        # Exception should be logged
        assert any("delivery error" in msg for msg in caplog.messages)
