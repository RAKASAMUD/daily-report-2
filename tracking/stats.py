"""Stats aggregation + confidence label — Task D1.

Pure functions; no I/O.
"""

from __future__ import annotations

from tracking.config import N_MIN_CONFIDENCE


def aggregate_stats(rows: list[tuple]) -> dict[tuple[str, str], dict]:
    """
    Aggregate outcome rows into per-(strategy, timeframe) statistics.

    rows: list of (strategy, timeframe, status, realized_r)
    Returns: {(strategy, timeframe): {"n", "wins", "win_rate", "expectancy"}}
    """
    groups: dict[tuple[str, str], list] = {}
    for strategy, timeframe, status, realized_r in rows:
        key = (strategy, timeframe)
        groups.setdefault(key, []).append((status, realized_r))

    result: dict[tuple[str, str], dict] = {}
    for key, outcomes in groups.items():
        n = len(outcomes)
        wins = sum(1 for status, _ in outcomes if status == "win")
        win_rate = wins / n
        expectancy = sum(r for _, r in outcomes) / n
        result[key] = {
            "n": n,
            "wins": wins,
            "win_rate": win_rate,
            "expectancy": expectancy,
        }
    return result


def confidence_label(
    group: dict | None,
    n_min: int = N_MIN_CONFIDENCE,
) -> str:
    """
    Return a human-readable confidence label.

    - None or group["n"] < n_min → "building (n=X)"
    - otherwise → "XX% TP-first (n=X)"
    """
    n = group["n"] if group else 0
    if group is None or n < n_min:
        return f"building (n={n})"
    pct = round(group["win_rate"] * 100)
    return f"{pct}% TP-first (n={n})"
