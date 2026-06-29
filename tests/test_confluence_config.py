from signal_engine.confluence_config import (
    CONFLUENCE_PARAMS, CONFLUENCE_CANDLE_LIMIT,
    ATR_MULT_BY_TF, MTF_PARENT, MTF_TREND_EMA, USE_MTF_FILTER
)
from data_layer.config import TIMEFRAMES

def test_confluence_config():
    assert isinstance(CONFLUENCE_PARAMS, dict)
    assert isinstance(CONFLUENCE_CANDLE_LIMIT, int)
    
    expected_keys = [
        "fast", "slow", "bb_period", "bb_std", "rsi_period", "rsi_threshold",
        "macd_fast", "macd_slow", "macd_signal", "vol_ma_period", "vol_mult",
        "stoch_k", "stoch_d", "stoch_threshold", "ema_trend", "sar_af_start",
        "sar_af_step", "sar_af_max", "atr_period", "rr",
        "atr_mult_by_tf", "mtf_parent", "mtf_trend_ema", "use_mtf_filter"
    ]
    for key in expected_keys:
        assert key in CONFLUENCE_PARAMS

    for tf in TIMEFRAMES:
        assert tf in ATR_MULT_BY_TF
        assert tf in MTF_PARENT
