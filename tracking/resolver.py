"""Resolver orchestration — Task C1.

I/O wrapper around the pure resolve() function.
Fetches pending signals, reads 5m candles, writes outcomes.
"""

import logging

from data_layer.db import get_candles_since
from data_layer.config import TIMEFRAME_MS
from tracking.config import TIMEOUT_BARS, ACTIVE_WINDOW_BUFFER_BARS
from tracking.resolve import resolve
from tracking.store import get_pending_signals, write_outcome

logger = logging.getLogger(__name__)


def run_resolver(
    conn,
    now_ms: int,
    timeout_bars: int = TIMEOUT_BARS,
    buffer_bars: int = ACTIVE_WINDOW_BUFFER_BARS,
) -> dict:
    """
    Drain pending signals: fetch candles, call resolve(), write outcomes.

    Per-signal isolation: exceptions are logged and counted in 'failed'.
    Returns {"pending": n, "resolved": int, "failed": int}.
    """
    pending = get_pending_signals(conn)
    resolved = 0
    failed = 0

    for sig in pending:
        tf_ms = TIMEFRAME_MS[sig.timeframe]
        entry_time = sig.bar_open_time + tf_ms
        age_bars = (now_ms - entry_time) / tf_ms

        if age_bars > timeout_bars + buffer_bars:
            logger.warning(
                "stale pending signal %s/%s/%s bot=%d (age=%.1f bars > %d+%d)",
                sig.symbol, sig.timeframe, sig.strategy, sig.bar_open_time,
                age_bars, timeout_bars, buffer_bars,
            )

        try:
            candles = get_candles_since(conn, sig.symbol, "5m", entry_time)
            o = resolve(sig, candles, timeout_bars)
            if o is not None and write_outcome(conn, o) == 1:
                resolved += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "resolver error for %s/%s/%s: %s",
                sig.symbol, sig.timeframe, sig.strategy, exc,
                exc_info=True,
            )
            failed += 1

    return {"pending": len(pending), "resolved": resolved, "failed": failed}
