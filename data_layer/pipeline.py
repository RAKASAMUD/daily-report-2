"""Sync pipeline — Task D1.

One function handles backfill, incremental update, and gap-fill identically:
it always fetches *from the last stored candle forward*.
"""

from data_layer.config import TIMEFRAME_MS
from data_layer.db import get_last_open_time, write_candles


def sync_pair(
    conn,
    adapter,
    symbol: str,
    timeframe: str,
    now_ms: int,
    backfill_days: int,
) -> int:
    """
    Fetch and store closed candles for one symbol/timeframe pair.

    Since calculation:
    - DB is empty  → since = now_ms - backfill_days * 86_400_000
    - DB has data  → since = last_open_time + TIMEFRAME_MS[timeframe]

    Returns the number of rows actually inserted (0 if nothing new).
    """
    tf_ms = TIMEFRAME_MS[timeframe]
    last = get_last_open_time(conn, symbol, timeframe)

    if last is None:
        since = now_ms - backfill_days * 86_400_000
    else:
        since = last + tf_ms

    rows = adapter.fetch_closed_ohlcv(symbol, timeframe, since, now_ms)
    return write_candles(conn, symbol, timeframe, rows)
