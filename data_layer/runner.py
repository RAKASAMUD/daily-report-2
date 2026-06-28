"""Tick runner — Task D2.

Responsibilities:
- floor_to_5min : align "now" to the 5-minute grid
- run_tick      : for each due timeframe × symbol, call sync_pair; isolate errors
- main          : single-instance lock, real ccxt exchange, connect + run_tick
"""

import logging
import os
import time

from data_layer.config import (
    BACKFILL_DAYS,
    DB_PATH,
    SYMBOLS,
    TIMEFRAME_MS,
    TIMEFRAMES,
)
from data_layer.db import connect, init_schema
from data_layer.logging_setup import setup_logging
from data_layer.pipeline import sync_pair
from data_layer.schedule import due_timeframes
from signal_engine.engine import run_engine
from signal_engine.registry import get_strategies
from signal_engine.store import init_signals_schema, migrate_signals_schema
from delivery.config import TARGET
from delivery.deliver import deliver_pending
from delivery.notifier import HermesNotifier

logger = logging.getLogger(__name__)

_5MIN_MS = 300_000  # milliseconds in 5 minutes
_LOCK_FILE = "data/runner.lock"


# ---------------------------------------------------------------------------
# floor_to_5min
# ---------------------------------------------------------------------------

def floor_to_5min(now_ms: int) -> int:
    """Floor an epoch-millisecond timestamp to the nearest 5-minute boundary."""
    return (now_ms // _5MIN_MS) * _5MIN_MS


# ---------------------------------------------------------------------------
# run_tick
# ---------------------------------------------------------------------------

def run_tick(
    conn,
    adapter,
    now_ms: int,
    symbols: list[str],
    timeframes: list[str],
    backfill_days: int,
) -> dict:
    """
    Run one 5-minute tick.

    1. Floor now_ms to the 5-minute grid.
    2. Determine which timeframes just closed.
    3. For each symbol × due timeframe: call sync_pair, catching all exceptions.

    Returns
    -------
    dict : {(symbol, timeframe): int_inserted | Exception}
        Only contains entries for pairs that were actually processed
        (i.e., whose timeframe was due). Empty dict if no timeframe is due.
    """
    now = floor_to_5min(now_ms)
    due = due_timeframes(now, timeframes)
    summary: dict = {}

    for symbol in symbols:
        for tf in due:
            try:
                inserted = sync_pair(conn, adapter, symbol, tf, now, backfill_days)
                summary[(symbol, tf)] = inserted
                logger.info("sync OK  %s/%s  inserted=%d", symbol, tf, inserted)
            except Exception as exc:  # noqa: BLE001
                summary[(symbol, tf)] = exc
                logger.warning(
                    "sync FAIL %s/%s  error=%s", symbol, tf, exc, exc_info=True
                )

    return summary


# ---------------------------------------------------------------------------
# run_delivery_step
# ---------------------------------------------------------------------------

def run_delivery_step(conn, now_ms: int, notifier=None) -> None:
    """
    Run the delivery step (outbox drain).
    Isolated in its own try/except so failures do not crash the runner.
    """
    migrate_signals_schema(conn)
    if notifier is None:
        notifier = HermesNotifier(TARGET)
        
    try:
        stats = deliver_pending(conn, notifier, now_ms=now_ms)
        logger.info(
            "delivery: attempted=%d sent=%d failed=%d",
            stats.get("attempted", 0), stats.get("sent", 0), stats.get("failed", 0)
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("delivery error: %s", exc, exc_info=True)


# ---------------------------------------------------------------------------
# main  (wiring only — not unit-tested; covered by E2)
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Entry point for the cron trigger.

    - Acquires an exclusive fcntl.flock on a lock file (exits immediately if
      another process already holds it — single-instance guarantee).
    - Builds a real ccxt.binance() exchange with enableRateLimit=True.
    - Connects to the SQLite DB and initialises the schema.
    - Runs one tick at now = time.time() * 1000.
    - Logs a one-line summary.
    """
    # Initialise logging first so every subsequent log line is captured
    setup_logging()

    # Single-instance lock (Unix only; no-op on Windows dev machines)
    lock_fh = None
    try:
        import fcntl  # noqa: PLC0415 — available on Linux VPS
        os.makedirs(os.path.dirname(_LOCK_FILE), exist_ok=True)
        lock_fh = open(_LOCK_FILE, "w")  # noqa: WPS515
        try:
            fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            logger.error("Another runner instance is already running. Exiting.")
            return
    except ImportError:
        # fcntl not available on Windows — skip locking during local dev
        logger.warning("fcntl not available; skipping single-instance lock.")

    try:
        import ccxt  # noqa: PLC0415

        exchange = ccxt.binance({"enableRateLimit": True})
        from data_layer.binance import BinanceAdapter

        adapter = BinanceAdapter(exchange)

        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = connect(DB_PATH)
        init_schema(conn)

        now_ms = int(time.time() * 1000)
        summary = run_tick(conn, adapter, now_ms, SYMBOLS, TIMEFRAMES, BACKFILL_DAYS)

        total_inserted = sum(v for v in summary.values() if isinstance(v, int))
        errors = [(k, v) for k, v in summary.items() if isinstance(v, Exception)]
        logger.info(
            "tick done: %d pairs processed, %d inserted, %d errors",
            len(summary),
            total_inserted,
            len(errors),
        )
        for (sym, tf), exc in errors:
            logger.warning("  failed: %s/%s — %s", sym, tf, exc)

        # ── Signal Engine (runs after ingestion is fully committed) ──────
        init_signals_schema(conn)   # idempotent — safe to call every tick
        try:
            new_signals = run_engine(conn, SYMBOLS, TIMEFRAMES, get_strategies())
            logger.info("engine: %d new signals", len(new_signals))
            # Stage 4 will consume `new_signals` here later.
        except Exception as eng_exc:  # noqa: BLE001
            logger.error("engine error (ingestion unharmed): %s", eng_exc, exc_info=True)

        # ── Delivery Engine (runs after signal engine) ───────────────────
        run_delivery_step(conn, now_ms)

    finally:
        if lock_fh is not None:
            lock_fh.close()


if __name__ == "__main__":
    main()
