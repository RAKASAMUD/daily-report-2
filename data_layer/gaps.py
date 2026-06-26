"""Gap detection logic — Task B3.

Pure function: no network, no DB, no clock.
"""

from data_layer.config import TIMEFRAME_MS


def find_missing(open_times: list[int], timeframe: str) -> list[int]:
    """
    Given a sorted list of open_times, return the open_times that *should*
    exist between the first and last entry (step = TIMEFRAME_MS[timeframe])
    but are absent.

    Returns [] for an empty list or a single-element list (no range to check).
    """
    if len(open_times) < 2:
        return []

    step = TIMEFRAME_MS[timeframe]
    existing = set(open_times)
    first, last = open_times[0], open_times[-1]

    missing = []
    t = first + step
    while t < last:
        if t not in existing:
            missing.append(t)
        t += step

    return missing
