"""Strategy registry — Task A2 (stub).

Registry wiring to ema_cross (C2) will be added once C2 exists.
For now, get_strategies() returns a placeholder empty list so tests can
assert structure; C2 will populate it.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional
import pandas as pd

from signal_engine.types import Signal

StrategyFn = Callable[[pd.DataFrame, dict], Optional[Signal]]


@dataclass
class RegisteredStrategy:
    name: str
    fn: StrategyFn
    params: dict
    timeframes: list[str]


# Internal registry list — populated by register() or direct append.
_REGISTRY: list[RegisteredStrategy] = []


def get_strategies() -> list[RegisteredStrategy]:
    """Return all registered strategies (stub — returns empty until C2 wires in)."""
    return list(_REGISTRY)
