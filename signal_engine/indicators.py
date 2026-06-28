"""Pure indicators — Task B1 (ema stub) + Task B2 (atr stub)."""

import pandas as pd
import numpy as np

def ema(values: pd.Series, period: int) -> pd.Series:
    """
    Standard Exponential Moving Average.

    Uses pandas ``ewm(span=period, adjust=False)`` which seeds EMA[0] = values[0]
    and applies the recurrence EMA[i] = alpha*values[i] + (1-alpha)*EMA[i-1]
    where alpha = 2/(period+1).

    No-lookahead by construction: value at index i uses only data up to i.
    """
    return values.ewm(span=period, adjust=False).mean()



def atr(df: pd.DataFrame, period: int) -> pd.Series:
    """
    Average True Range with Wilder smoothing.

    True Range at bar i:
        TR[0] = high[0] - low[0]   (no previous close)
        TR[i] = max(high[i]-low[i], |high[i]-close[i-1]|, |low[i]-close[i-1]|)

    Wilder smoothing (alpha = 1/period):
        ATR[0] = TR[0]
        ATR[i] = alpha * TR[i] + (1-alpha) * ATR[i-1]

    df must have columns: high, low, close  (ascending by open_time).
    Value at index i uses only data up to i — no lookahead.
    """
    high  = df["high"]
    low   = df["low"]
    close = df["close"]

    prev_close = close.shift(1)

    # True range — for bar 0 there is no previous close, so only h-l applies
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)

    # Bar 0: TR only (prev_close is NaN → the other two terms are NaN → max = h-l)
    # pandas max(axis=1) with skipna=True handles this correctly already.

    # Wilder smoothing: ewm with alpha=1/period, adjust=False
    # seeds the first value = TR[0] automatically.
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


def bollinger_bands(
    close: pd.Series, period: int = 20, num_std: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands (Middle, Upper, Lower).

    Middle = Simple Moving Average (SMA).
    Std    = Rolling standard deviation (ddof=0 for population std).
    Upper  = Middle + num_std * Std
    Lower  = Middle - num_std * Std

    The first `period - 1` values will be NaN.
    """
    middle = close.rolling(period).mean()
    std = close.rolling(period).std(ddof=0)
    upper = middle + num_std * std
    lower = middle - num_std * std
    return middle, upper, lower


def ema_slope_falling(ema_series: pd.Series, lookback: int) -> bool:
    """
    Check if EMA is falling.
    Returns True if ema_series.iloc[-1] < ema_series.iloc[-1 - lookback].
    If the series is not long enough, returns False.
    """
    if len(ema_series) <= lookback:
        return False
    return bool(ema_series.iloc[-1] < ema_series.iloc[-1 - lookback])

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    
    roll_up = up.ewm(alpha=1/period, adjust=False).mean()
    roll_down = down.ewm(alpha=1/period, adjust=False).mean()
    
    rs = roll_up / roll_down
    # when roll_down is 0, rs is inf, which makes rsi 100
    rsi_vals = np.where(roll_down == 0, 100, 100.0 - (100.0 / (1.0 + rs)))
    return pd.Series(rsi_vals, index=close.index)

def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> tuple[pd.Series, pd.Series]:
    lowest_low = df["low"].rolling(window=k_period).min()
    highest_high = df["high"].rolling(window=k_period).max()
    
    k = (df["close"] - lowest_low) / (highest_high - lowest_low) * 100
    d = k.rolling(window=d_period).mean()
    return k, d

def parabolic_sar(df: pd.DataFrame, af_start: float = 0.02, af_step: float = 0.02, af_max: float = 0.2) -> pd.Series:
    high = df['high'].values
    low = df['low'].values
    n = len(df)
    
    sar = np.zeros(n)
    if n == 0:
        return pd.Series(sar, index=df.index)
        
    sar[0] = low[0]
    bull = True
    af = af_start
    ep = high[0]
    
    for i in range(1, n):
        sar[i] = sar[i-1] + af * (ep - sar[i-1])
        
        if bull:
            sar[i] = min(sar[i], low[i-1])
            if i > 1:
                sar[i] = min(sar[i], low[i-2])
                
            if low[i] < sar[i]:
                bull = False
                sar[i] = ep
                af = af_start
                ep = low[i]
            else:
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + af_step, af_max)
        else:
            sar[i] = max(sar[i], high[i-1])
            if i > 1:
                sar[i] = max(sar[i], high[i-2])
                
            if high[i] > sar[i]:
                bull = True
                sar[i] = ep
                af = af_start
                ep = high[i]
            else:
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + af_step, af_max)
                    
    return pd.Series(sar, index=df.index)
