"""Tests for signal_engine.strategy — Task C1: strategy contract."""

import pandas as pd
import pytest

from signal_engine.strategy import StrategyFn, dummy_strategy


def _make_df(n: int = 5) -> pd.DataFrame:
    """Small candle DataFrame for contract tests."""
    return pd.DataFrame({
        "open_time": [1_700_000_000_000 + i * 300_000 for i in range(n)],
        "open":  [100.0 + i for i in range(n)],
        "high":  [105.0 + i for i in range(n)],
        "low":   [ 95.0 + i for i in range(n)],
        "close": [102.0 + i for i in range(n)],
        "volume":[1000.0   for _ in range(n)],
    })


class TestStrategyContract:
    def test_dummy_strategy_returns_none(self):
        """dummy_strategy always returns None."""
        df = _make_df()
        result = dummy_strategy(df, {})
        assert result is None

    def test_dummy_strategy_is_callable(self):
        """dummy_strategy is callable."""
        assert callable(dummy_strategy)

    def test_dummy_strategy_satisfies_type(self):
        """dummy_strategy signature matches StrategyFn."""
        # Verify it can be assigned to StrategyFn-typed variable without error
        fn: StrategyFn = dummy_strategy
        assert fn(_make_df(), {}) is None

    def test_strategy_fn_does_not_mutate_df(self):
        """
        Calling a strategy must not mutate the input DataFrame.
        Purity guard: compare df before and after calling dummy_strategy.
        """
        df = _make_df()
        df_copy = df.copy(deep=True)
        dummy_strategy(df, {"some_param": 42})
        pd.testing.assert_frame_equal(df, df_copy)

    def test_strategy_accepts_empty_params(self):
        """Strategy must handle empty params dict without error."""
        df = _make_df()
        result = dummy_strategy(df, {})
        assert result is None

    def test_strategy_accepts_extra_params(self):
        """Strategy must tolerate extra/unknown keys in params."""
        df = _make_df()
        result = dummy_strategy(df, {"foo": 1, "bar": "baz", "n": 99})
        assert result is None
