"""Tests for signal_engine.config + registry — Task A2."""

import pytest

from data_layer.config import TIMEFRAMES
from signal_engine.config import EMA_CROSS_PARAMS, CANDLE_LIMIT
from signal_engine.registry import get_strategies, RegisteredStrategy


# ---------------------------------------------------------------------------
# Tests: config
# ---------------------------------------------------------------------------

class TestEmaCrossParams:
    _REQUIRED_KEYS = {"fast", "slow", "trend", "use_trend_filter",
                      "atr_period", "atr_mult", "rr"}

    def test_has_all_required_keys(self):
        assert self._REQUIRED_KEYS <= EMA_CROSS_PARAMS.keys()

    def test_fast_less_than_slow(self):
        assert EMA_CROSS_PARAMS["fast"] < EMA_CROSS_PARAMS["slow"]

    def test_slow_less_than_trend(self):
        assert EMA_CROSS_PARAMS["slow"] < EMA_CROSS_PARAMS["trend"]

    def test_rr_positive(self):
        assert EMA_CROSS_PARAMS["rr"] > 0

    def test_atr_mult_positive(self):
        assert EMA_CROSS_PARAMS["atr_mult"] > 0

    def test_use_trend_filter_is_bool(self):
        assert isinstance(EMA_CROSS_PARAMS["use_trend_filter"], bool)


class TestCandleLimit:
    def test_candle_limit_value(self):
        assert CANDLE_LIMIT == 300

    def test_candle_limit_exceeds_trend_period(self):
        """CANDLE_LIMIT must be > trend EMA period to allow warmup."""
        assert CANDLE_LIMIT > EMA_CROSS_PARAMS["trend"]


# ---------------------------------------------------------------------------
# Tests: registry
# ---------------------------------------------------------------------------

class TestGetStrategies:
    def test_returns_list(self):
        result = get_strategies()
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_each_entry_is_registered_strategy(self):
        """Every entry must be a RegisteredStrategy instance."""
        for entry in get_strategies():
            assert isinstance(entry, RegisteredStrategy)

    def test_each_entry_has_callable_fn(self):
        for entry in get_strategies():
            assert callable(entry.fn)

    def test_each_entry_timeframes_subset_of_stage1(self):
        """Strategy timeframes must be a subset of Stage 1 TIMEFRAMES."""
        for entry in get_strategies():
            assert set(entry.timeframes) <= set(TIMEFRAMES), (
                f"{entry.name} has timeframes not in Stage 1 TIMEFRAMES"
            )

    def test_each_entry_params_has_required_keys(self):
        """
        If a strategy is named 'ema_cross', its params must contain
        EMA_CROSS_PARAMS keys. Generalised: params must be a dict.
        """
        for entry in get_strategies():
            assert isinstance(entry.params, dict)
            if entry.name == "ema_cross":
                required = {"fast", "slow", "trend", "use_trend_filter",
                            "atr_period", "atr_mult", "rr"}
                assert required <= entry.params.keys()
            elif entry.name == "bollinger_mr":
                required = {"bb_period", "bb_std", "ema_trend", "slope_lookback",
                            "use_downtrend_filter", "atr_period", "sl_buffer_atr",
                            "min_rr", "depth_med", "depth_high"}
                assert required <= entry.params.keys()

    def test_registered_strategy_has_name(self):
        for entry in get_strategies():
            assert isinstance(entry.name, str) and entry.name
