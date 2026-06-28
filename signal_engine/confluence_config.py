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
    "atr_mult": 1.5,
    "rr": 2.0,
}

CONFLUENCE_CANDLE_LIMIT: int = 300
