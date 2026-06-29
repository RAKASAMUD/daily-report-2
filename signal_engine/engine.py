"""Signal engine — Task D1.

Evaluates all registered strategies across every (symbol, timeframe) pair,
stores new signals with INSERT OR IGNORE dedup, and returns only newly
inserted signals (those that weren't already in the DB).

Design decisions:
- Per-(strategy, symbol, tf) try/except: one bad combination never stops others.
- Strategy only runs on timeframes listed in strat.timeframes.
- Engine injects symbol and timeframe into params so the strategy can stamp them.
"""

import logging

from data_layer.db import get_candles
from signal_engine.confluence_config import CONFLUENCE_CANDLE_LIMIT, MTF_PARENT, MTF_TREND_EMA
from signal_engine.mtf import compute_all_mtf_states
from signal_engine.registry import RegisteredStrategy
from signal_engine.store import write_signal
from signal_engine.types import Signal

logger = logging.getLogger(__name__)


def run_engine(
    conn,
    symbols: list[str],
    timeframes: list[str],
    strategies: list[RegisteredStrategy],
    candle_limit: int = CONFLUENCE_CANDLE_LIMIT,
) -> list[Signal]:
    """
    Evaluate all strategies × symbols × timeframes.

    For each (strategy, symbol, timeframe) triple:
      1. Fetch the last `candle_limit` candles from the DB.
      2. Call strategy.fn(df, params) to get a Signal or None.
      3. If a Signal is returned, attempt INSERT OR IGNORE.
      4. If the insert succeeded (new row), add to the returned list.

    Exceptions inside a strategy are caught and logged — they never
    propagate out of the engine.

    Returns
    -------
    list[Signal] — only signals that were newly inserted this run.
    """
    new_signals: list[Signal] = []

    mtf_states = compute_all_mtf_states(conn, symbols, MTF_PARENT, MTF_TREND_EMA, candle_limit)

    for strat in strategies:
        eligible_tfs = set(timeframes) & set(strat.timeframes)
        for symbol in symbols:
            for tf in eligible_tfs:
                try:
                    df = get_candles(conn, symbol, tf, limit=candle_limit)
                    params = {**strat.params, "symbol": symbol, "timeframe": tf}
                    mtf_aligned = mtf_states.get((symbol, tf))
                    sig = strat.fn(df, params, mtf_aligned=mtf_aligned)
                    if sig is not None:
                        inserted = write_signal(conn, sig)
                        if inserted == 1:
                            new_signals.append(sig)
                except Exception as exc:
                    logger.warning(
                        "engine error [%s %s %s]: %s",
                        strat.name, symbol, tf, exc,
                        exc_info=True,
                    )

    # ── Per-tick summary ─────────────────────────────────────────────────
    logger.info("engine: %d new signal(s) this tick", len(new_signals))
    for sig in new_signals:
        logger.info(
            "  signal: %s / %s / %s  entry=%.4f  tp=%.4f  sl=%.4f  rr=%.2f",
            sig.symbol, sig.timeframe, sig.strategy,
            sig.entry, sig.tp, sig.sl, sig.rr,
        )

    return new_signals
