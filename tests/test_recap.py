"""Tests for weekly recap — Task E1."""

import pytest
from tracking.stats import aggregate_stats
from scripts.weekly_recap import build_recap


def _stats(rows):
    return aggregate_stats(rows)


class TestBuildRecap:
    def test_empty_stats_shows_no_signals_message(self):
        text = build_recap({})
        assert "no resolved signals" in text.lower()

    def test_single_group_rendered(self):
        stats = _stats([
            ("ema_cross", "1h", "win",  2.0),
            ("ema_cross", "1h", "win",  2.0),
            ("ema_cross", "1h", "loss", -1.0),
        ])
        text = build_recap(stats)
        assert "ema_cross" in text
        assert "1h" in text
        # n=3 is in the table as a column, not "n=3" string; check the column value
        assert "   3" in text   # right-aligned n column
        # win_rate = 2/3 = 66% or 67% (rounding)
        assert "66%" in text or "67%" in text
        # expectancy = (2+2-1)/3 = 1.0
        assert "1.00" in text

    def test_multiple_groups_all_rendered(self):
        stats = _stats([
            ("ema_cross",   "1h", "win",  2.0),
            ("ema_cross",   "4h", "loss", -1.0),
            ("rsi_reversal","1h", "win",  1.5),
        ])
        text = build_recap(stats)
        assert "ema_cross" in text
        assert "rsi_reversal" in text
        assert "4h" in text

    def test_recap_includes_expectancy_header(self):
        stats = _stats([("ema_cross", "1h", "win", 2.0)])
        text = build_recap(stats)
        assert "expectancy" in text.lower() or "E[R]" in text

    def test_recap_sorted_by_strategy_then_timeframe(self):
        stats = _stats([
            ("ema_cross",   "4h", "win", 2.0),
            ("ema_cross",   "1h", "win", 2.0),
            ("atr_breakout","1h", "win", 1.5),
        ])
        text = build_recap(stats)
        lines = [l for l in text.splitlines() if l.strip()]
        # Find lines with strategy names
        strat_lines = [l for l in lines if any(s in l for s in ("atr_breakout", "ema_cross"))]
        # Should appear: atr_breakout/1h, ema_cross/1h, ema_cross/4h
        assert strat_lines[0].startswith("atr_breakout") or "atr_breakout" in strat_lines[0]
