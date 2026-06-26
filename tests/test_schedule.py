"""Tests for data_layer.schedule — Task B2: due_timeframes boundary logic."""

import pytest
from datetime import datetime, timezone

from data_layer.schedule import due_timeframes
from data_layer.config import TIMEFRAMES


# ---------------------------------------------------------------------------
# Helper: convert a UTC datetime to epoch milliseconds
# ---------------------------------------------------------------------------

def utc_ms(year, month, day, hour=0, minute=0, second=0) -> int:
    dt = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDueTimeframes:
    def test_4h_boundary_returns_all_timeframes(self):
        # 2024-01-01 04:00:00 UTC — divisible by 5m, 15m, 1h, 4h
        now = utc_ms(2024, 1, 1, hour=4)
        result = due_timeframes(now, TIMEFRAMES)
        assert result == ["5m", "15m", "1h", "4h"]

    def test_5m_only_boundary(self):
        # 2024-01-01 04:05:00 UTC — divisible by 5m only
        now = utc_ms(2024, 1, 1, hour=4, minute=5)
        result = due_timeframes(now, TIMEFRAMES)
        assert result == ["5m"]

    def test_15m_boundary_returns_5m_and_15m(self):
        # 2024-01-01 04:15:00 UTC — divisible by 5m and 15m
        now = utc_ms(2024, 1, 1, hour=4, minute=15)
        result = due_timeframes(now, TIMEFRAMES)
        assert result == ["5m", "15m"]

    def test_1h_boundary_returns_5m_15m_1h(self):
        # 2024-01-01 05:00:00 UTC — divisible by 5m, 15m, 1h (not 4h)
        now = utc_ms(2024, 1, 1, hour=5)
        result = due_timeframes(now, TIMEFRAMES)
        assert result == ["5m", "15m", "1h"]

    def test_order_matches_input_order(self):
        # At a 4h boundary, order must follow input list order
        now = utc_ms(2024, 1, 1, hour=8)
        custom_order = ["4h", "1h", "15m", "5m"]
        result = due_timeframes(now, custom_order)
        assert result == ["4h", "1h", "15m", "5m"]

    def test_midnight_boundary_returns_all(self):
        # 2024-01-01 00:00:00 UTC — divisible by all timeframes
        now = utc_ms(2024, 1, 1, hour=0)
        result = due_timeframes(now, TIMEFRAMES)
        assert result == ["5m", "15m", "1h", "4h"]

    def test_non_boundary_returns_empty(self):
        # 2024-01-01 04:03:00 UTC — not on any 5m boundary
        now = utc_ms(2024, 1, 1, hour=4, minute=3)
        result = due_timeframes(now, TIMEFRAMES)
        assert result == []

    def test_returns_list(self):
        now = utc_ms(2024, 1, 1, hour=4)
        result = due_timeframes(now, TIMEFRAMES)
        assert isinstance(result, list)
