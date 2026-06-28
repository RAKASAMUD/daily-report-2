from signal_engine.confluence_config import CONFLUENCE_PARAMS, CONFLUENCE_CANDLE_LIMIT

def test_confluence_config():
    assert isinstance(CONFLUENCE_PARAMS, dict)
    assert isinstance(CONFLUENCE_CANDLE_LIMIT, int)
    
    expected_keys = [
        "fast", "slow", "bb_period", "bb_std", "rsi_period", "rsi_threshold",
        "macd_fast", "macd_slow", "macd_signal", "vol_ma_period", "vol_mult",
        "stoch_k", "stoch_d", "stoch_threshold", "ema_trend", "sar_af_start",
        "sar_af_step", "sar_af_max", "atr_period", "atr_mult", "rr"
    ]
    for key in expected_keys:
        assert key in CONFLUENCE_PARAMS
        assert type(CONFLUENCE_PARAMS[key]) in (int, float)
