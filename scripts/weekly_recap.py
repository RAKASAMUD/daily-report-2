"""Weekly recap script — Task E1.

Aggregates resolved outcomes and sends a summary via hermes.
Intended for cron: 0 0 * * 1  <venv>/python -m scripts.weekly_recap >> .../recap.log 2>&1
"""

import logging
import sys
from datetime import datetime, timezone

from data_layer.config import DB_PATH
from data_layer.db import connect
from data_layer.logging_setup import setup_logging
from delivery.config import TARGET
from delivery.notifier import HermesNotifier
from tracking.store import get_outcome_rows
from tracking.stats import aggregate_stats

logger = logging.getLogger(__name__)


def build_recap(stats: dict) -> str:
    """
    Pure: build a weekly recap text from an aggregate_stats dict.
    
    stats: {(strategy, timeframe): {"n", "wins", "win_rate", "expectancy"}}
    Returns a formatted string ready to send.
    """
    now_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    header = f"📊 Weekly Recap — {now_str} UTC\n"
    sep = "─" * 38

    if not stats:
        return header + sep + "\nNo resolved signals yet. Keep running!\n" + sep

    lines = [header, sep]
    lines.append(f"{'Strategy / TF':<22} {'n':>4}  {'Win%':>5}  {'E[R]':>6}")
    lines.append(sep)

    for (strategy, timeframe) in sorted(stats.keys()):
        g = stats[(strategy, timeframe)]
        win_pct = round(g["win_rate"] * 100)
        expectancy = g["expectancy"]
        label = f"{strategy}/{timeframe}"
        lines.append(f"{label:<22} {g['n']:>4}  {win_pct:>4}%  {expectancy:>+6.2f}R")

    lines.append(sep)
    return "\n".join(lines) + "\n"


def main() -> None:
    setup_logging()

    try:
        conn = connect(DB_PATH)
    except Exception as exc:
        logger.error("Could not connect to database: %s", exc)
        sys.exit(1)

    try:
        rows = get_outcome_rows(conn)
    except Exception as exc:
        logger.error("Could not read outcome rows: %s", exc)
        sys.exit(1)

    stats = aggregate_stats(rows)
    text = build_recap(stats)

    print(text)  # always echo to stdout / log

    notifier = HermesNotifier(TARGET)
    ok = notifier.send(text)
    if not ok:
        logger.warning("weekly recap send failed — check hermes config")
        sys.exit(1)

    logger.info("weekly recap sent (%d groups)", len(stats))


if __name__ == "__main__":
    main()
