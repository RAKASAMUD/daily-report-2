"""One-time backlog resolution script — Task E2.

Run once on VPS after deploy to resolve all historical pending signals
using already-stored 5m candle history.

Usage:
    python -m scripts.resolve_backlog
"""

import logging
import sys

from data_layer.config import DB_PATH
from data_layer.db import connect
from data_layer.logging_setup import setup_logging
from signal_engine.store import init_signals_schema
from tracking.store import init_outcomes_schema, get_pending_signals
from tracking.resolver import run_resolver
import time

logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging()

    logger.info("Starting one-time backlog resolution...")

    try:
        conn = connect(DB_PATH)
    except Exception as exc:
        logger.error("Could not connect to database: %s", exc)
        sys.exit(1)

    # Ensure schemas exist
    init_signals_schema(conn)
    init_outcomes_schema(conn)

    pending_before = get_pending_signals(conn)
    logger.info("Pending signals before resolution: %d", len(pending_before))

    if not pending_before:
        logger.info("No pending signals found. Nothing to resolve.")
        return

    now_ms = int(time.time() * 1000)
    stats = run_resolver(conn, now_ms=now_ms)

    logger.info(
        "Backlog resolution complete: pending=%d resolved=%d failed=%d",
        stats["pending"],
        stats["resolved"],
        stats["failed"],
    )

    pending_after = get_pending_signals(conn)
    logger.info(
        "Remaining pending signals: %d (signals still within window or missing candle data)",
        len(pending_after),
    )


if __name__ == "__main__":
    main()
