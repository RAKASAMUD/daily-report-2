"""Outcome dataclass — Task A1."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Outcome:
    symbol: str
    timeframe: str
    strategy: str
    bar_open_time: int
    status: str              # "win" | "loss" | "expired"
    realized_r: float
    bars_to_resolution: int
    resolved_at: int         # epoch ms
    resolution_price: float
