import pandas as pd
import numpy as np
from signal_engine.checks import (
    CheckResult,
    check_ema_cross,
    check_bollinger_bounce,
    check_rsi_recovery,
    check_macd_cross,
    check_volume_spike,
    check_stochastic_recovery,
    check_ema200_cross,
    check_sar_flip,
    ALL_CHECKS
)

def build_df(close_vals, vols=None):
    n = len(close_vals)
    if vols is None:
        vols = [1000] * n
    return pd.DataFrame({
        "open": close_vals,
        "high": np.array(close_vals) + 1,
        "low": np.array(close_vals) - 1,
        "close": close_vals,
        "volume": vols
    })

def test_all_checks_len():
    assert len(ALL_CHECKS) == 8

def test_checks_no_crash():
    df = build_df([10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10, 9, 8, 7, 8, 9, 10, 11, 12, 13] * 3)
    for check in ALL_CHECKS:
        res = check(df, {})
        assert isinstance(res, CheckResult)

def test_ema_cross_transition():
    params = {"fast": 2, "slow": 5}
    # Before transition
    df = build_df([10, 10, 10, 10, 10, 10, 10])
    res = check_ema_cross(df, params)
    assert not res.triggered

    # Transition
    df = build_df([10, 10, 10, 10, 10, 10, 20])
    res = check_ema_cross(df, params)
    assert res.triggered
    assert "EMA2 > EMA5" in res.detail

    # Already triggered
    df = build_df([10, 10, 15, 20, 20, 20, 20])
    res = check_ema_cross(df, params)
    assert not res.triggered
