from dataclasses import dataclass
from typing import Callable
import pandas as pd
from signal_engine.indicators import ema, bollinger_bands, rsi, macd, stochastic, parabolic_sar

@dataclass(frozen=True)
class CheckResult:
    name: str
    triggered: bool
    detail: str

def check_ema_cross(df: pd.DataFrame, params: dict) -> CheckResult:
    fast = params.get("fast", 20)
    slow = params.get("slow", 50)
    
    close = df["close"]
    if len(close) < 2:
        return CheckResult("EMA Cross", False, "")
        
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    
    prev_fast = ema_fast.iloc[-2]
    prev_slow = ema_slow.iloc[-2]
    curr_fast = ema_fast.iloc[-1]
    curr_slow = ema_slow.iloc[-1]
    
    triggered = (prev_fast <= prev_slow) and (curr_fast > curr_slow)
    detail = f"EMA{fast} > EMA{slow}" if triggered else ""
    return CheckResult("EMA Cross", triggered, detail)

def check_bollinger_bounce(df: pd.DataFrame, params: dict) -> CheckResult:
    period = params.get("bb_period", 20)
    std = params.get("bb_std", 2.0)
    
    close = df["close"]
    if len(close) < 2:
        return CheckResult("Bollinger Bounce", False, "")
        
    _, _, lower = bollinger_bands(close, period, std)
    
    prev_close = close.iloc[-2]
    prev_lower = lower.iloc[-2]
    curr_close = close.iloc[-1]
    curr_lower = lower.iloc[-1]
    
    triggered = (prev_close < prev_lower) and (curr_close >= curr_lower)
    detail = "Bounce off lower BB" if triggered else ""
    return CheckResult("Bollinger Bounce", triggered, detail)

def check_rsi_recovery(df: pd.DataFrame, params: dict) -> CheckResult:
    period = params.get("rsi_period", 14)
    threshold = params.get("rsi_threshold", 30)
    
    close = df["close"]
    if len(close) < 2:
        return CheckResult("RSI Recovery", False, "")
        
    rsi_vals = rsi(close, period)
    
    prev_rsi = rsi_vals.iloc[-2]
    curr_rsi = rsi_vals.iloc[-1]
    
    triggered = (prev_rsi < threshold) and (curr_rsi >= threshold)
    detail = f"RSI: {int(curr_rsi)}" if triggered else ""
    return CheckResult("RSI Recovery", triggered, detail)

def check_macd_cross(df: pd.DataFrame, params: dict) -> CheckResult:
    fast = params.get("macd_fast", 12)
    slow = params.get("macd_slow", 26)
    signal = params.get("macd_signal", 9)
    
    close = df["close"]
    if len(close) < 2:
        return CheckResult("MACD Cross", False, "")
        
    macd_line, signal_line, _ = macd(close, fast, slow, signal)
    
    prev_macd = macd_line.iloc[-2]
    prev_signal = signal_line.iloc[-2]
    curr_macd = macd_line.iloc[-1]
    curr_signal = signal_line.iloc[-1]
    
    triggered = (prev_macd <= prev_signal) and (curr_macd > curr_signal)
    detail = "MACD bullish cross" if triggered else ""
    return CheckResult("MACD Cross", triggered, detail)

def check_volume_spike(df: pd.DataFrame, params: dict) -> CheckResult:
    period = params.get("vol_ma_period", 20)
    mult = params.get("vol_mult", 1.5)
    
    vol = df["volume"]
    if len(vol) < period:
        return CheckResult("Volume Spike", False, "")
        
    vol_sma = vol.rolling(period).mean()
    
    prev_vol = vol.iloc[-2]
    prev_sma = vol_sma.iloc[-2]
    curr_vol = vol.iloc[-1]
    curr_sma = vol_sma.iloc[-1]
    
    triggered = (prev_vol < mult * prev_sma) and (curr_vol >= mult * curr_sma)
    detail = f"{curr_vol/curr_sma:.1f}x avg volume" if (triggered and curr_sma > 0) else ""
    return CheckResult("Volume Spike", triggered, detail)

def check_stochastic_recovery(df: pd.DataFrame, params: dict) -> CheckResult:
    k_period = params.get("stoch_k", 14)
    d_period = params.get("stoch_d", 3)
    threshold = params.get("stoch_threshold", 20)
    
    if len(df) < k_period:
        return CheckResult("Stochastic Recovery", False, "")
        
    k, d = stochastic(df, k_period, d_period)
    
    prev_k = k.iloc[-2]
    curr_k = k.iloc[-1]
    curr_d = d.iloc[-1]
    
    triggered = (prev_k < threshold) and (curr_k >= threshold) and (curr_k > curr_d)
    detail = f"%K: {int(curr_k)}" if triggered else ""
    return CheckResult("Stochastic Recovery", triggered, detail)

def check_ema200_cross(df: pd.DataFrame, params: dict) -> CheckResult:
    trend = params.get("ema_trend", 200)
    
    close = df["close"]
    if len(close) < 2:
        return CheckResult("EMA200 Cross", False, "")
        
    ema200 = ema(close, trend)
    
    prev_close = close.iloc[-2]
    prev_ema = ema200.iloc[-2]
    curr_close = close.iloc[-1]
    curr_ema = ema200.iloc[-1]
    
    triggered = (prev_close <= prev_ema) and (curr_close > curr_ema)
    detail = f"Price > EMA{trend}" if triggered else ""
    return CheckResult("EMA200 Cross", triggered, detail)

def check_sar_flip(df: pd.DataFrame, params: dict) -> CheckResult:
    af_start = params.get("sar_af_start", 0.02)
    af_step = params.get("sar_af_step", 0.02)
    af_max = params.get("sar_af_max", 0.2)
    
    if len(df) < 2:
        return CheckResult("SAR Flip", False, "")
        
    try:
        sar = parabolic_sar(df, af_start, af_step, af_max)
        close = df["close"]
        
        prev_sar = sar.iloc[-2]
        prev_close = close.iloc[-2]
        curr_sar = sar.iloc[-1]
        curr_close = close.iloc[-1]
        
        triggered = (prev_sar > prev_close) and (curr_sar < curr_close)
        detail = "SAR bullish flip" if triggered else ""
        return CheckResult("SAR Flip", triggered, detail)
    except Exception:
        return CheckResult("SAR Flip", False, "")

ALL_CHECKS: list[Callable] = [
    check_ema_cross,
    check_bollinger_bounce,
    check_rsi_recovery,
    check_macd_cross,
    check_volume_spike,
    check_stochastic_recovery,
    check_ema200_cross,
    check_sar_flip
]
