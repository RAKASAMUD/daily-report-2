"""Tests for data_layer.gaps — Task B3: gap detection over open_time continuity."""

import pytest

from data_layer.gaps import find_missing
from data_layer.config import TIMEFRAME_MS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_contiguous(start_ms: int, timeframe: str, n: int) -> list[int]:
    """Generate n contiguous open_times starting from start_ms."""
    step = TIMEFRAME_MS[timeframe]
    return [start_ms + i * step for i in range(n)]


# ---------------------------------------------------------------------------
# Tests: find_missing
# ---------------------------------------------------------------------------

class TestFindMissing:
    def test_contiguous_series_returns_empty(self):
        times = make_contiguous(1_000_000_000, "5m", 10)
        result = find_missing(times, "5m")
        assert result == []

    def test_single_element_returns_empty(self):
        result = find_missing([1_000_000_000], "5m")
        assert result == []

    def test_one_hole_in_middle(self):
        times = make_contiguous(1_000_000_000, "5m", 6)
        # Remove index 3 to punch a hole
        missing_time = times[3]
        times_with_hole = times[:3] + times[4:]
        result = find_missing(times_with_hole, "5m")
        assert result == [missing_time]

    def test_multiple_holes(self):
        times = make_contiguous(1_000_000_000, "15m", 8)
        # Remove indices 2 and 5
        expected_missing = [times[2], times[5]]
        times_with_holes = [t for i, t in enumerate(times) if i not in (2, 5)]
        result = find_missing(times_with_holes, "15m")
        assert result == expected_missing

    def test_hole_at_start_boundary(self):
        """Gap immediately after the first element."""
        times = make_contiguous(1_000_000_000, "1h", 5)
        missing_time = times[1]
        times_with_hole = [times[0]] + times[2:]
        result = find_missing(times_with_hole, "1h")
        assert result == [missing_time]

    def test_hole_at_end_boundary(self):
        """Gap immediately before the last element."""
        times = make_contiguous(1_000_000_000, "4h", 5)
        missing_time = times[3]
        times_with_hole = times[:3] + [times[4]]
        result = find_missing(times_with_hole, "4h")
        assert result == [missing_time]

    def test_different_timeframes_use_correct_step(self):
        # Contiguous 1h series should not flag as missing with "1h"
        times = make_contiguous(1_000_000_000, "1h", 5)
        assert find_missing(times, "1h") == []

    def test_returns_list(self):
        times = make_contiguous(1_000_000_000, "5m", 5)
        result = find_missing(times, "5m")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Property-style test: random_walk_candles contiguous series → no gaps
# ---------------------------------------------------------------------------

class TestFindMissingProperty:
    def test_random_walk_candles_fully_contiguous(self):
        """A fully generated series must yield no missing open_times."""
        from data_layer.testkit import random_walk_candles

        for tf in ["5m", "15m", "1h", "4h"]:
            rows = random_walk_candles(
                start_open_time=1_700_000_000_000,
                timeframe=tf,
                n=50,
                seed=42,
            )
            open_times = [r[0] for r in rows]
            missing = find_missing(open_times, tf)
            assert missing == [], f"Expected no gaps for {tf}, got {missing}"

    def test_random_walk_candles_deterministic(self):
        """Same seed must produce identical open_times."""
        from data_layer.testkit import random_walk_candles

        rows_a = random_walk_candles(1_700_000_000_000, "5m", 20, seed=1)
        rows_b = random_walk_candles(1_700_000_000_000, "5m", 20, seed=1)
        assert [r[0] for r in rows_a] == [r[0] for r in rows_b]
