"""Configuration constants for the data layer."""

SYMBOLS: list[str] = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "SUI/USDT",
    "AVAX/USDT",
]

TIMEFRAMES: list[str] = ["5m", "15m", "1h", "4h"]

TIMEFRAME_MS: dict[str, int] = {
    "5m":  300_000,
    "15m": 900_000,
    "1h":  3_600_000,
    "4h":  14_400_000,
}

BACKFILL_DAYS: int = 730

DB_PATH: str = "data/candles.db"
