"""Signal dataclass — Task A1."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Signal:
    symbol: str
    timeframe: str
    strategy: str
    bar_open_time: int      # epoch ms of the trigger (last-closed) bar
    direction: str          # "long"
    entry: float
    tp: float
    sl: float
    rr: float               # effective (tp-entry)/(entry-sl)
    reason: str
    strength: str           # "low" | "med" | "high"
    created_at: int         # epoch ms when detected
