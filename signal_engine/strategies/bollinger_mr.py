"""Mean-Reversion Bollinger Strategy ("Buy on Low") — Develop 2 Task B1."""

import time
import pandas as pd

from signal_engine.types import Signal
from signal_engine.indicators import bollinger_bands, ema, atr, ema_slope_falling


def bollinger_mean_reversion(df: pd.DataFrame, params: dict) -> Signal | None:
    """
    Mean-reversion strategy based on Bollinger Bands.
    
    1. Wait for price to dip below the lower Bollinger Band.
    2. Wait for a confirmation candle that closes back above the lower band.
    3. Enter long on confirmation close.
    4. TP at the middle band (SMA20).
    5. SL below the lowest point of the dip minus ATR buffer.
    """
    # Need enough data for indicators (EMA200, BB)
    if len(df) < params["ema_trend"] or len(df) < params["bb_period"]:
        return None

    close = df["close"]
    low = df["low"]
    
    # 1. Compute indicators
    mid, upper, lower_band = bollinger_bands(close, params["bb_period"], params["bb_std"])
    ema200 = ema(close, params["ema_trend"])
    atrv = atr(df, params["atr_period"]).iloc[-1]
    
    # 2. Transition check (bounce confirmation)
    was_below = close.iloc[-2] < lower_band.iloc[-2]
    now_above = close.iloc[-1] >= lower_band.iloc[-1]
    
    if not (was_below and now_above):
        return None
        
    # 3. Anti-downtrend filter
    use_filter = params.get("use_downtrend_filter", True)
    filter_reason = ""
    if use_filter:
        is_below_ema200 = close.iloc[-1] < ema200.iloc[-1]
        is_falling = ema_slope_falling(ema200, params["slope_lookback"])
        
        if is_below_ema200 and is_falling:
            return None
        
        if is_below_ema200 and not is_falling:
            filter_reason = ", close<EMA200 but EMA200 flat/rising"
        else:
            filter_reason = ", close>EMA200"

    # 4. Find dip low
    # Scan backwards from iloc[-2] (the last bar still below band) collecting lows
    dip_low = low.iloc[-2]
    idx = len(df) - 2
    
    # Keep going back as long as close was below its respective lower band
    while idx >= 0 and close.iloc[idx] < lower_band.iloc[idx]:
        if low.iloc[idx] < dip_low:
            dip_low = low.iloc[idx]
        idx -= 1
        
    # 5. Compute levels
    entry = close.iloc[-1]
    tp = mid.iloc[-1]
    sl = dip_low - params["sl_buffer_atr"] * atrv
    
    # Structural check
    if sl >= entry or tp <= entry:
        return None
        
    rr = (tp - entry) / (entry - sl)
    if rr < params["min_rr"]:
        return None
        
    # 6. Strength
    # how far below the band was the close at iloc[-2]
    depth_pct = (lower_band.iloc[-2] - close.iloc[-2]) / lower_band.iloc[-2] * 100
    
    if depth_pct >= params["depth_high"]:
        strength = "high"
    elif depth_pct >= params["depth_med"]:
        strength = "med"
    else:
        strength = "low"
        
    # 7. Build Signal
    reason = f"Bounce off lower BB (dip {depth_pct:.1f}% below band){filter_reason}"
    
    return Signal(
        symbol=params["symbol"],
        timeframe=params["timeframe"],
        strategy="bollinger_mr",
        bar_open_time=int(df["open_time"].iloc[-1]),
        direction="long",
        entry=entry,
        tp=tp,
        sl=sl,
        rr=rr,
        reason=reason,
        strength=strength,
        created_at=int(time.time() * 1000)
    )
