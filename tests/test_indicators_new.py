import pandas as pd
import numpy as np
import pytest
from signal_engine.indicators import rsi, macd, stochastic, parabolic_sar

def test_rsi():
    close = pd.Series([10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10, 9, 8, 7, 8, 9, 10, 11, 12, 13])
    rsi_vals = rsi(close, period=14)
    assert len(rsi_vals) == len(close)
    assert (rsi_vals.dropna() >= 0).all()
    assert (rsi_vals.dropna() <= 100).all()

def test_macd():
    close = pd.Series([10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10, 9, 8, 7, 8, 9, 10, 11, 12, 13] * 5)
    macd_line, signal_line, hist = macd(close, fast=12, slow=26, signal=9)
    assert len(macd_line) == len(close)
    assert len(signal_line) == len(close)
    assert len(hist) == len(close)
    assert (hist.dropna() == (macd_line - signal_line).dropna()).all()

def test_stochastic():
    df = pd.DataFrame({
        "high": [10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10, 9, 8, 7, 8, 9, 10],
        "low":  [8,  9,  10, 11, 12, 13, 12, 11, 10, 9,  8,  7, 6, 5, 6, 7, 8],
        "close":[9,  10, 11, 12, 13, 14, 13, 12, 11, 10, 9,  8, 7, 6, 7, 8, 9]
    })
    k, d = stochastic(df, k_period=14, d_period=3)
    assert len(k) == len(df)
    assert len(d) == len(df)
    assert (k.dropna() >= 0).all()
    assert (k.dropna() <= 100).all()

def test_parabolic_sar():
    df = pd.DataFrame({
        "high": [10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10, 9, 8, 7, 8, 9, 10],
        "low":  [8,  9,  10, 11, 12, 13, 12, 11, 10, 9,  8,  7, 6, 5, 6, 7, 8],
        "close":[9,  10, 11, 12, 13, 14, 13, 12, 11, 10, 9,  8, 7, 6, 7, 8, 9]
    })
    sar_vals = parabolic_sar(df, af_start=0.02, af_step=0.02, af_max=0.2)
    assert len(sar_vals) == len(df)
    assert isinstance(sar_vals, pd.Series)
