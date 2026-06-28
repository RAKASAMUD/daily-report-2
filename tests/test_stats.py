"""Tests for tracking.stats — Task D1."""

import pytest
from tracking.stats import aggregate_stats, confidence_label
from tracking.config import N_MIN_CONFIDENCE


def _rows(*entries):
    """Build outcome rows: each entry is (strategy, timeframe, status, realized_r)."""
    return list(entries)


class TestAggregateStats:
    def test_single_win_group(self):
        rows = _rows(("ema_cross", "1h", "win", 2.0))
        stats = aggregate_stats(rows)
        g = stats[("ema_cross", "1h")]
        assert g["n"] == 1
        assert g["wins"] == 1
        assert g["win_rate"] == pytest.approx(1.0)
        assert g["expectancy"] == pytest.approx(2.0)

    def test_mixed_win_loss_expired(self):
        rows = _rows(
            ("ema_cross", "1h", "win",     2.0),
            ("ema_cross", "1h", "win",     2.0),
            ("ema_cross", "1h", "loss",   -1.0),
            ("ema_cross", "1h", "expired", 0.0),
        )
        stats = aggregate_stats(rows)
        g = stats[("ema_cross", "1h")]
        assert g["n"] == 4
        assert g["wins"] == 2
        assert g["win_rate"] == pytest.approx(0.5)
        # expectancy = (2+2-1+0)/4 = 0.75
        assert g["expectancy"] == pytest.approx(0.75)

    def test_expired_counts_in_n_and_lowers_win_rate(self):
        rows = _rows(
            ("ema_cross", "1h", "win",     2.0),
            ("ema_cross", "1h", "expired",-0.5),
            ("ema_cross", "1h", "expired",-0.5),
        )
        stats = aggregate_stats(rows)
        g = stats[("ema_cross", "1h")]
        assert g["n"] == 3
        assert g["wins"] == 1
        assert g["win_rate"] == pytest.approx(1 / 3)

    def test_multiple_groups_kept_separate(self):
        rows = _rows(
            ("ema_cross", "1h",  "win", 2.0),
            ("ema_cross", "4h",  "loss", -1.0),
            ("rsi_reversal", "1h", "win", 1.5),
        )
        stats = aggregate_stats(rows)
        assert len(stats) == 3
        assert stats[("ema_cross", "1h")]["wins"] == 1
        assert stats[("ema_cross", "4h")]["wins"] == 0
        assert stats[("rsi_reversal", "1h")]["wins"] == 1

    def test_empty_rows_returns_empty_dict(self):
        assert aggregate_stats([]) == {}


class TestConfidenceLabel:
    def test_below_n_min_shows_building(self):
        group = {"n": 5, "wins": 3, "win_rate": 0.6, "expectancy": 1.0}
        label = confidence_label(group, n_min=20)
        assert label == "building (n=5)"

    def test_exactly_n_min_shows_percentage(self):
        group = {"n": 20, "wins": 14, "win_rate": 0.7, "expectancy": 1.0}
        label = confidence_label(group, n_min=20)
        assert label == "70% TP-first (n=20)"

    def test_above_n_min_shows_percentage(self):
        group = {"n": 50, "wins": 35, "win_rate": 0.7, "expectancy": 1.2}
        label = confidence_label(group, n_min=20)
        assert label == "70% TP-first (n=50)"

    def test_none_group_shows_building_zero(self):
        label = confidence_label(None, n_min=20)
        assert label == "building (n=0)"

    def test_uses_n_min_confidence_default(self):
        group = {"n": N_MIN_CONFIDENCE - 1, "wins": 10, "win_rate": 0.5, "expectancy": 0.5}
        label = confidence_label(group)
        assert "building" in label

    def test_win_rate_rounded_to_integer_percent(self):
        group = {"n": 25, "wins": 17, "win_rate": 17/25, "expectancy": 1.0}
        label = confidence_label(group, n_min=20)
        # 17/25 = 0.68 → round to 68%
        assert label == "68% TP-first (n=25)"
