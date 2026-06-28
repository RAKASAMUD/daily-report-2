"""Strategy contract — Task C1 (stub).

Defines StrategyFn type alias and a minimal dummy_strategy
to pin the contract before real strategies are built in C2.
"""

from typing import Callable, Optional
import pandas as pd

from signal_engine.types import Signal

# Type alias: any strategy function must match this signature
StrategyFn = Callable[[pd.DataFrame, dict], Optional[Signal]]


def dummy_strategy(df: pd.DataFrame, params: dict) -> Optional[Signal]:
    """
    Placeholder strategy that always returns None.

    Used to pin the StrategyFn contract in tests before real strategies
    (C2 onwards) are implemented. Does not mutate df.
    """
    return None

