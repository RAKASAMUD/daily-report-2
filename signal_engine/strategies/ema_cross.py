"""EMA cross strategy — Task C2 (Setup #1).

Signal fires once at the *transition bar* where fast EMA crosses above slow EMA.
Trend filter (optional): requires close > EMA_trend at the trigger bar.
Entry, SL, TP are computed from ATR at entry; RR is exact by construction.
"""

import time
from typing import Optional

import pandas as pd

from signal_engine.indicators import atr, ema
from signal_engine.types import Signal


def ema_cross(df: pd.DataFrame, params: dict) -> Optional[Signal]:
    """
    EMA cross strategy — long only, event-driven at the transition bar.

    Parameters read from params
    ---------------------------
    fast            : int   — fast EMA period
    slow            : int   — slow EMA period
    trend           : int   — trend EMA period (only used when use_trend_filter=True)
    use_trend_filter: bool  — if True, close must be > EMA_trend to fire
    atr_period      : int   — ATR period for SL/TP sizing
    atr_mult        : float — SL = entry - atr_mult * ATR
    rr              : float — TP = entry + rr * (entry - SL)
    symbol          : str   — injected by the engine
    timeframe       : str   — injected by the engine
    created_at      : int   — epoch ms (optional, defaults to now)

    Returns
    -------
    Signal if this bar is a fresh cross (and filter passes), else None.
    """
    # ── Guard: need at least 3 rows (current + previous for cross check) ──
    if len(df) < 3:
        return None

    fast_period = params["fast"]
    slow_period = params["slow"]
    trend_period = params["trend"]
    use_trend_filter = params["use_trend_filter"]
    atr_period = params["atr_period"]
    atr_mult = params["atr_mult"]
    rr_target = params["rr"]
    symbol = params.get("symbol", "UNKNOWN")
    timeframe = params.get("timeframe", "UNKNOWN")
    created_at = params.get("created_at", int(time.time() * 1000))

    close = df["close"]

    # ── EMA cross detection ──────────────────────────────────────────────
    fast_ema = ema(close, fast_period)
    slow_ema = ema(close, slow_period)

    # Fresh cross: fast just crossed above slow at the last bar
    fresh_cross = (
        fast_ema.iloc[-1] > slow_ema.iloc[-1]
        and fast_ema.iloc[-2] <= slow_ema.iloc[-2]
    )
    if not fresh_cross:
        return None

    # ── Trend filter ─────────────────────────────────────────────────────
    reason_parts = [f"EMA{fast_period}>EMA{slow_period} cross"]
    if use_trend_filter:
        trend_ema_val = ema(close, trend_period).iloc[-1]
        if close.iloc[-1] <= trend_ema_val:
            return None
        reason_parts.append(f"close>EMA{trend_period}")

    reason = ", ".join(reason_parts)

    # ── Entry, SL, TP, RR ────────────────────────────────────────────────
    entry = float(close.iloc[-1])
    atrv = float(atr(df, atr_period).iloc[-1])

    sl = entry - atr_mult * atrv
    tp = entry + rr_target * (entry - sl)
    effective_rr = (tp - entry) / (entry - sl)  # == rr_target by construction

    return Signal(
        symbol=symbol,
        timeframe=timeframe,
        strategy="ema_cross",
        bar_open_time=int(df["open_time"].iloc[-1]),
        direction="long",
        entry=entry,
        tp=tp,
        sl=sl,
        rr=effective_rr,
        reason=reason,
        created_at=created_at,
    )
