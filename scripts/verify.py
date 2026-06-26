"""On-demand integrity verify tool — Task E3.

Usage (command line):
    python -m scripts.verify

For each symbol × timeframe:
  1. Read all open_times from the DB.
  2. Run find_missing to detect gaps.
  3. If an adapter is given (real run), fetch + fill any holes via sync_pair.
  4. Print a summary report.
"""

import logging

from data_layer.config import BACKFILL_DAYS, SYMBOLS, TIMEFRAMES
from data_layer.db import get_candles
from data_layer.gaps import find_missing
from data_layer.pipeline import sync_pair

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core logic (unit-testable)
# ---------------------------------------------------------------------------

def verify_pair(
    conn,
    adapter,
    symbol: str,
    timeframe: str,
    now_ms: int,
) -> dict:
    """
    Check integrity for one symbol/timeframe pair.

    1. Read all stored open_times (using a large limit to get everything).
    2. Find missing open_times with find_missing.
    3. If adapter is provided and gaps exist, call sync_pair to fill them.

    Returns
    -------
    dict with keys:
        symbol      : str
        timeframe   : str
        gaps        : list[int]  — missing open_times before filling
        gaps_found  : int
        filled      : int        — rows inserted during this call (0 if no adapter)
    """
    # Fetch all rows — use a very large limit to get everything
    df = get_candles(conn, symbol, timeframe, limit=10_000_000)
    open_times: list[int] = list(df["open_time"]) if not df.empty else []

    gaps = find_missing(open_times, timeframe) if len(open_times) >= 2 else []
    gaps_found = len(gaps)
    filled = 0

    if gaps and adapter is not None:
        # sync_pair will fetch from the last stored candle forward,
        # which covers the gap window naturally
        filled = sync_pair(conn, adapter, symbol, timeframe, now_ms, BACKFILL_DAYS)
        logger.info(
            "verify %s/%s: filled %d of %d gaps", symbol, timeframe, filled, gaps_found
        )
    elif gaps_found > 0:
        logger.warning(
            "verify %s/%s: %d gaps found (no adapter — not filled)", symbol, timeframe, gaps_found
        )
    else:
        logger.info("verify %s/%s: OK (no gaps)", symbol, timeframe)

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "gaps": gaps,
        "gaps_found": gaps_found,
        "filled": filled,
    }


def verify_all(
    conn,
    adapter,
    symbols: list[str],
    timeframes: list[str],
    now_ms: int,
) -> list[dict]:
    """
    Run verify_pair for every symbol × timeframe combination.

    Returns a list of report dicts (one per pair).
    """
    reports = []
    for symbol in symbols:
        for timeframe in timeframes:
            report = verify_pair(conn, adapter, symbol, timeframe, now_ms)
            reports.append(report)
    return reports


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run verify against the real DB and print a summary."""
    import time
    from data_layer.db import connect, init_schema
    from data_layer.logging_setup import setup_logging

    setup_logging()

    try:
        import ccxt
        from data_layer.binance import BinanceAdapter
        from data_layer.config import DB_PATH

        exchange = ccxt.binance({"enableRateLimit": True})
        adapter = BinanceAdapter(exchange)

        conn = connect(DB_PATH)
        init_schema(conn)
        now_ms = int(time.time() * 1000)

        print("\n=== Data Layer Integrity Verify ===\n")
        reports = verify_all(conn, adapter, SYMBOLS, TIMEFRAMES, now_ms)

        total_gaps = sum(r["gaps_found"] for r in reports)
        total_filled = sum(r["filled"] for r in reports)

        for r in reports:
            status = "✓ OK" if r["gaps_found"] == 0 else f"✗ {r['gaps_found']} gaps"
            fill_info = f" | filled {r['filled']}" if r["filled"] > 0 else ""
            print(f"  {r['symbol']:12s} {r['timeframe']:4s}  {status}{fill_info}")

        print(f"\nTotal: {total_gaps} gaps found, {total_filled} filled.\n")

    except Exception as exc:
        logger.error("verify failed: %s", exc, exc_info=True)
        raise


if __name__ == "__main__":
    main()
