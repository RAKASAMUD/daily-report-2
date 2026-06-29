ATR_MULT_BY_TF: dict = {
    "5m": 2.5,
    "15m": 2.0,
    "1h": 1.5,
    "4h": 1.5,
}

MTF_PARENT: dict = {
    "5m": "1h",
    "15m": "1h",
    "1h": "4h",
    "4h": None,
}

MTF_TREND_EMA: int = 50
USE_MTF_FILTER: bool = True

CONFLUENCE_PARAMS: dict = {
    # EMA cross
    "fast": 20,
    "slow": 50,
    # Bollinger
    "bb_period": 20,
    "bb_std": 2.0,
    # RSI
    "rsi_period": 14,
    "rsi_threshold": 30,
    # MACD
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    # Volume
    "vol_ma_period": 20,
    "vol_mult": 1.5,
    # Stochastic
    "stoch_k": 14,
    "stoch_d": 3,
    "stoch_threshold": 20,
    # EMA200
    "ema_trend": 200,
    # SAR
    "sar_af_start": 0.02,
    "sar_af_step": 0.02,
    "sar_af_max": 0.2,
    # Trade levels (universal ATR-based)
    "atr_period": 14,
    "rr": 2.0,
    "atr_mult_by_tf": ATR_MULT_BY_TF,
    "mtf_parent": MTF_PARENT,
    "mtf_trend_ema": MTF_TREND_EMA,
    "use_mtf_filter": USE_MTF_FILTER,
}

CONFLUENCE_CANDLE_LIMIT: int = 300
