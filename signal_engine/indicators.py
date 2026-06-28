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
    """True Range with Wilder smoothing — no-lookahead (stub)."""
    pass  # stub
