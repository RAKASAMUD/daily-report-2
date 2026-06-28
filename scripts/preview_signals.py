"""Preview signal cards — Task E1.

Loads the most recent N signals from the database and prints their
formatted text representation. Does not send anything.
"""

import argparse
import sys
import logging
from typing import Optional

from data_layer.config import DB_PATH
from data_layer.db import connect
from data_layer.logging_setup import setup_logging
from signal_engine.store import get_signals
from delivery.format import format_signal

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview formatted signal cards from the DB.")
    parser.add_argument(
        "--limit", type=int, default=5,
        help="Number of most recent signals to preview (default: 5)"
    )
    args = parser.parse_args()

    setup_logging()
    
    try:
        conn = connect(DB_PATH)
    except Exception as exc:
        logger.error("Could not connect to database: %s", exc)
        sys.exit(1)

    # We use get_signals directly to get the most recent ones, regardless of whether 
    # they were delivered or not. (get_signals returns them in ascending order of time)
    import sqlite3
    try:
        signals = get_signals(conn, limit=args.limit)
    except sqlite3.OperationalError as exc:
        if "no such table: signals" in str(exc):
            print("No signals found in the database (table does not exist yet).")
            return
        else:
            raise
    
    if not signals:
        print("No signals found in the database.")
        return

    print(f"--- PREVIEWING MOST RECENT {len(signals)} SIGNALS ---")
    
    # Reverse so the newest is at the bottom (or just iterate ascending)
    # get_signals returns ascending (oldest first up to the most recent `limit`).
    # Let's just print them in the order they're returned.
    for i, sig in enumerate(signals, 1):
        print(f"\n[{i}/{len(signals)}] Signal from {sig.symbol} ({sig.timeframe}):")
        print("=" * 40)
        print(format_signal(sig))
        print("=" * 40)


if __name__ == "__main__":
    main()
