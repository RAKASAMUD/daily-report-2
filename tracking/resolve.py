"""Pure outcome resolution — Task B1.

Resolves a Signal to WIN / LOSS / EXPIRED using stored 5m candles.
No I/O — all DB access is in resolver.py (C1).
"""

from __future__ import annotations

import pandas as pd

from data_layer.config import TIMEFRAME_MS
from signal_engine.types import Signal
from tracking.types import Outcome


def resolve(
    signal: Signal,
    candles_5m: pd.DataFrame,
    timeout_bars: int,
) -> Outcome | None:
    """
    Scan 5m candles from entry_time forward.

    Rules (long-only):
    - entry_time = signal.bar_open_time + TIMEFRAME_MS[signal.timeframe]
    - deadline   = entry_time + timeout_bars * TIMEFRAME_MS[signal.timeframe]
    - hit_sl = low  <= signal.sl   (pessimistic ambiguity: SL first if both hit)
    - hit_tp = high >= signal.tp
    - WIN  realized_r = signal.rr ; LOSS realized_r = -1.0
    - EXPIRED: resolution_price = close of last candle whose open_time <= deadline
               realized_r = min(0.0, (resolution_price - entry) / (entry - sl))
               bars_to_resolution = timeout_bars
    - Still PENDING: return None
    """
    tf_ms = TIMEFRAME_MS[signal.timeframe]
    entry_time = signal.bar_open_time + tf_ms
    deadline = entry_time + timeout_bars * tf_ms

    # Filter: only candles at or after entry_time (no-lookahead)
    post_entry = candles_5m[candles_5m["open_time"] >= entry_time].copy()

    # Scan for TP/SL hit
    for _, row in post_entry.iterrows():
        hit_sl = row["low"] <= signal.sl
        hit_tp = row["high"] >= signal.tp

        if hit_sl or hit_tp:
            # bars_to_resolution = how many signal-tf bars elapsed from entry_time to this candle
            bars_elapsed = int((row["open_time"] - entry_time) // tf_ms)

            if hit_sl:
                # Pessimistic: SL first (covers ambiguity case too)
                return Outcome(
                    symbol=signal.symbol,
                    timeframe=signal.timeframe,
                    strategy=signal.strategy,
                    bar_open_time=signal.bar_open_time,
                    status="loss",
                    realized_r=-1.0,
                    bars_to_resolution=bars_elapsed,
                    resolved_at=int(row["open_time"]),
                    resolution_price=signal.sl,
                )
            else:
                # hit_tp only
                return Outcome(
                    symbol=signal.symbol,
                    timeframe=signal.timeframe,
                    strategy=signal.strategy,
                    bar_open_time=signal.bar_open_time,
                    status="win",
                    realized_r=signal.rr,
                    bars_to_resolution=bars_elapsed,
                    resolved_at=int(row["open_time"]),
                    resolution_price=signal.tp,
                )

    # No hit — check if window is fully elapsed
    # We need at least one candle with open_time >= deadline to confirm window is over
    past_deadline = candles_5m[candles_5m["open_time"] >= deadline]
    if past_deadline.empty:
        return None  # Still PENDING

    # EXPIRED — find the last candle with open_time <= deadline for resolution price
    at_or_before_deadline = candles_5m[candles_5m["open_time"] <= deadline]
    if at_or_before_deadline.empty:
        # Edge case: no candles in the resolution window at all
        return None

    resolution_price = float(at_or_before_deadline.iloc[-1]["close"])
    entry = signal.entry
    sl = signal.sl
    realized_r = min(0.0, (resolution_price - entry) / (entry - sl))

    return Outcome(
        symbol=signal.symbol,
        timeframe=signal.timeframe,
        strategy=signal.strategy,
        bar_open_time=signal.bar_open_time,
        status="expired",
        realized_r=realized_r,
        bars_to_resolution=timeout_bars,
        resolved_at=int(deadline),
        resolution_price=resolution_price,
    )
