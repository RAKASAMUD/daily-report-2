"""Scheduling logic — Task B2.

Pure decision logic: which timeframes just closed at a given timestamp.
Never calls time.time() — clock is always injected via now_ms.
"""

from data_layer.config import TIMEFRAME_MS


def due_timeframes(now_ms: int, timeframes: list[str]) -> list[str]:
    """
    Return the subset of timeframes whose candle just closed at now_ms.

    A timeframe is due when now_ms is an exact multiple of TIMEFRAME_MS[tf],
    meaning the prior candle of that timeframe closed exactly at this boundary.

    Order of the returned list matches the order of the input timeframes list.
    """
    return [tf for tf in timeframes if now_ms % TIMEFRAME_MS[tf] == 0]
