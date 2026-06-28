"""Pure indicators — Task B1 (ema stub) + Task B2 (atr stub)."""

import pandas as pd


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

