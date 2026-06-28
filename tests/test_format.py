"""Tests for delivery.format — Task B1."""

import pytest
from datetime import datetime, timezone

from signal_engine.types import Signal
from delivery.format import format_signal


def _make_signal(
    direction="long",
    entry=60305.0,
    tp=62100.0,
    sl=59400.0,
    strength="high",
) -> Signal:
    # 2026-06-28 07:00:00 UTC = 1782630000000 ms
    # Let's just use 1782630000000 for predictability
    return Signal(
        symbol="BTC/USDT",
        timeframe="1h",
        strategy="ema_cross",
        bar_open_time=1782630000000,
        direction=direction,
        entry=entry,
        tp=tp,
        sl=sl,
        rr=2.0,
        reason="EMA20>EMA50 cross, close>EMA200",
        strength=strength,
        created_at=1782630060000,
    )


class TestFormatSignal:
    def test_format_signal_standard(self):
        sig = _make_signal()
        card = format_signal(sig)
        
        # Check title line
        assert "📈 LONG · BTC/USDT · 1h" in card
        # Check Setup
        assert "Setup: EMA20>EMA50 cross, close>EMA200" in card
        # Check formatting of numbers (thousands separator)
        assert "Entry: 60,305" in card
        assert "TP:    62,100" in card
        assert "SL:    59,400" in card
        # Check percentages
        # tp_pct = (62100 - 60305) / 60305 * 100 = 2.976...
        # formatting to .1f should be +3.0%
        assert "(+3.0%)" in card
        # sl_pct = (59400 - 60305) / 60305 * 100 = -1.500...
        assert "(-1.5%)" in card
        # Check RR
        assert "R:R:   2.0" in card
        # Check strength
        assert "Strength: HIGH" in card
        # Check bar time
        assert "Bar:   2026-06-28 07:00 UTC" in card

    def test_format_signal_missing_strength(self):
        sig = _make_signal(strength="")
        card = format_signal(sig)
        assert "Strength: n/a" in card
        
        sig_none = _make_signal(strength=None) # type: ignore
        card_none = format_signal(sig_none)
        assert "Strength: n/a" in card_none

    def test_format_signal_small_numbers(self):
        """Test with small numbers like 0.05 to ensure they are formatted properly."""
        sig = _make_signal(entry=0.05, tp=0.052, sl=0.049)
        card = format_signal(sig)
        # 0.05 formatted with strip trailing zeros
        assert "Entry: 0.05" in card
        assert "TP:    0.052" in card
        assert "SL:    0.049" in card
        assert "(+4.0%)" in card
        assert "(-2.0%)" in card


# ---------------------------------------------------------------------------
# Task D2 tests — confidence line
# ---------------------------------------------------------------------------

class TestFormatSignalConfidence:
    def test_no_stats_shows_building_zero(self):
        sig = _make_signal()
        card = format_signal(sig, stats=None)
        assert "Confidence: building (n=0)" in card

    def test_sparse_group_shows_building(self):
        sig = _make_signal()
        stats = {("ema_cross", "1h"): {"n": 5, "wins": 3, "win_rate": 0.6, "expectancy": 1.0}}
        card = format_signal(sig, stats=stats)
        assert "Confidence: building (n=5)" in card

    def test_sufficient_group_shows_percentage(self):
        sig = _make_signal()
        stats = {("ema_cross", "1h"): {"n": 25, "wins": 18, "win_rate": 0.72, "expectancy": 1.1}}
        card = format_signal(sig, stats=stats)
        assert "Confidence: 72% TP-first (n=25)" in card

    def test_formatter_is_pure_no_db_access(self):
        """Formatter takes stats dict in, not a db conn — no side effects."""
        sig = _make_signal()
        stats = {("ema_cross", "1h"): {"n": 30, "wins": 21, "win_rate": 0.7, "expectancy": 1.0}}
        # Calling twice returns identical results (pure)
        assert format_signal(sig, stats=stats) == format_signal(sig, stats=stats)
