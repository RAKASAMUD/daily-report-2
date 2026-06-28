"""Strategy registry — Task A2 / C2 wiring.

Registers all strategies. Currently: ema_cross (Setup #1).
Add new strategies here: one RegisteredStrategy entry per strategy file.
"""

from dataclasses import dataclass
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


# Internal registry — populated at module import time.
_REGISTRY: list[RegisteredStrategy] = []


def _build_registry() -> None:
    """Populate the registry. Called once at module load."""
    from signal_engine.strategies.ema_cross import ema_cross
    from signal_engine.config import EMA_CROSS_PARAMS, CANDLE_LIMIT
    from data_layer.config import TIMEFRAMES

    _REGISTRY.append(
        RegisteredStrategy(
            name="ema_cross",
            fn=ema_cross,
            params=EMA_CROSS_PARAMS,
            timeframes=TIMEFRAMES,
        )
    )


_build_registry()


def get_strategies() -> list[RegisteredStrategy]:
    """Return all registered strategies."""
    return list(_REGISTRY)
