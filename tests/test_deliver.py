"""Tests for delivery.deliver — Task C1."""

import pytest

from data_layer.db import connect
from signal_engine.types import Signal
from signal_engine.store import init_signals_schema, migrate_signals_schema, write_signal, get_undelivered
from delivery.deliver import deliver_pending


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
    def __init__(self, fail_on_symbol=None, raise_on_symbol=None):
        self.sent_messages = []
        self.fail_on_symbol = fail_on_symbol
        self.raise_on_symbol = raise_on_symbol

    def send(self, message: str) -> bool:
        if self.raise_on_symbol and self.raise_on_symbol in message:
            raise RuntimeError("Fake network error")
        if self.fail_on_symbol and self.fail_on_symbol in message:
            return False
        self.sent_messages.append(message)
        return True


def fake_formatter(sig: Signal) -> str:
    return f"Card for {sig.symbol}"


class TestDeliverPending:
    def test_all_success(self):
        conn = _make_conn()
        write_signal(conn, _make_signal("S1", 1000))
        write_signal(conn, _make_signal("S2", 2000))

        notifier = FakeNotifier()
        stats = deliver_pending(conn, notifier, 9999, max_per_tick=10, formatter=fake_formatter)

        assert stats == {"attempted": 2, "sent": 2, "failed": 0}
        assert len(notifier.sent_messages) == 2
        
        # Verify db updated
        assert len(get_undelivered(conn, 10)) == 0

    def test_send_returns_false_for_one_signal(self):
        conn = _make_conn()
        write_signal(conn, _make_signal("S1", 1000))
        write_signal(conn, _make_signal("S2", 2000)) # this one will fail

        notifier = FakeNotifier(fail_on_symbol="S2")
        stats = deliver_pending(conn, notifier, 9999, max_per_tick=10, formatter=fake_formatter)

        assert stats == {"attempted": 2, "sent": 1, "failed": 1}
        assert len(notifier.sent_messages) == 1
        
        # S2 should still be undelivered
        undelivered = get_undelivered(conn, 10)
        assert len(undelivered) == 1
        assert undelivered[0].symbol == "S2"

    def test_notifier_raises_for_one_signal(self):
        """A notifier that raises on one signal \u2192 loop continues, that one stays NULL."""
        conn = _make_conn()
        write_signal(conn, _make_signal("S1", 1000)) # will raise
        write_signal(conn, _make_signal("S2", 2000))

        notifier = FakeNotifier(raise_on_symbol="S1")
        stats = deliver_pending(conn, notifier, 9999, max_per_tick=10, formatter=fake_formatter)

        assert stats == {"attempted": 2, "sent": 1, "failed": 1}
        assert len(notifier.sent_messages) == 1
        
        # S1 should still be undelivered
        undelivered = get_undelivered(conn, 10)
        assert len(undelivered) == 1
        assert undelivered[0].symbol == "S1"

    def test_respects_max_per_tick(self):
        """more than max_per_tick undelivered \u2192 only max_per_tick attempted."""
        conn = _make_conn()
        for i in range(5):
            write_signal(conn, _make_signal(f"S{i}", 1000 + i))

        notifier = FakeNotifier()
        stats = deliver_pending(conn, notifier, 9999, max_per_tick=3, formatter=fake_formatter)

        assert stats == {"attempted": 3, "sent": 3, "failed": 0}
        assert len(notifier.sent_messages) == 3
        
        # 2 remain undelivered
        assert len(get_undelivered(conn, 10)) == 2

    def test_idempotent_empty_db(self):
        """a second deliver_pending after all sent \u2192 attempts 0."""
        conn = _make_conn()
        write_signal(conn, _make_signal("S1", 1000))

        notifier = FakeNotifier()
        stats1 = deliver_pending(conn, notifier, 9999, max_per_tick=10, formatter=fake_formatter)
        assert stats1["attempted"] == 1

        stats2 = deliver_pending(conn, notifier, 9999, max_per_tick=10, formatter=fake_formatter)
        assert stats2 == {"attempted": 0, "sent": 0, "failed": 0}
