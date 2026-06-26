"""Backfill script — Task E1.

Runs sync_pair once for every symbol × timeframe against the real Binance API,
seeding the DB with up to BACKFILL_DAYS of historical candles.

Usage:
    python -m scripts.backfill
"""

import logging
import time

import ccxt

from data_layer.binance import BinanceAdapter
from data_layer.config import BACKFILL_DAYS, DB_PATH, SYMBOLS, TIMEFRAMES
from data_layer.db import connect, init_schema
from data_layer.logging_setup import setup_logging
from data_layer.pipeline import sync_pair

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging()
    logger.info("Starting backfill: %d symbols × %d timeframes, %d days history",
                len(SYMBOLS), len(TIMEFRAMES), BACKFILL_DAYS)

    exchange = ccxt.binance({"enableRateLimit": True})
    adapter = BinanceAdapter(exchange)

    import os
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = connect(DB_PATH)
    init_schema(conn)

    now_ms = int(time.time() * 1000)
    total_inserted = 0

    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            try:
                inserted = sync_pair(conn, adapter, symbol, tf, now_ms, BACKFILL_DAYS)
                total_inserted += inserted
                logger.info("  %-12s %-4s  inserted=%d", symbol, tf, inserted)
            except Exception as exc:
                logger.warning("  %-12s %-4s  FAILED: %s", symbol, tf, exc, exc_info=True)

    logger.info("Backfill complete. Total rows inserted: %d", total_inserted)


if __name__ == "__main__":
    main()
