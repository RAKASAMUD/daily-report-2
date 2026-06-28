"""Delivery driver — Task C1."""

import logging

from delivery.config import MAX_PER_TICK
from delivery.format import format_signal
from delivery.notifier import Notifier
from signal_engine.store import get_undelivered, mark_sent

logger = logging.getLogger(__name__)


def deliver_pending(
    conn,
    notifier: Notifier,
    now_ms: int,
    max_per_tick: int = MAX_PER_TICK,
    formatter=format_signal,
) -> dict:
    """
    Drain the outbox: fetch undelivered signals, format, and send.
    
    If send succeeds, mark as sent. If it fails or raises, leave it NULL 
    for retry on the next tick. Isolated per signal.
    """
    rows = get_undelivered(conn, max_per_tick)
    sent = 0
    failed = 0

    for sig in rows:
        try:
            message = formatter(sig)
            if notifier.send(message):
                mark_sent(conn, sig, now_ms)
                sent += 1
            else:
                failed += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "delivery failed for signal %s/%s/%s: %s",
                sig.symbol, sig.timeframe, sig.strategy, exc,
                exc_info=True
            )
            failed += 1

    return {"attempted": len(rows), "sent": sent, "failed": failed}
