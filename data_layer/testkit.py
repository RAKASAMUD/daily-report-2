"""Test helpers — Tasks B3 + C1.

Provides:
- FakeExchange  : ccxt-like fake for unit tests (no network)
- random_walk_candles : deterministic OHLCV generator
"""

import random

from data_layer.config import TIMEFRAME_MS

# Type alias matching the plan: (open_time, open, high, low, close, volume)
Row = tuple[int, float, float, float, float, float]


# ---------------------------------------------------------------------------
# random_walk_candles
# ---------------------------------------------------------------------------

def random_walk_candles(
    start_open_time: int,
    timeframe: str,
    n: int,
    seed: int,
    start_price: float = 100.0,
) -> list[Row]:
    """
    Generate n deterministic OHLCV candle rows for the given timeframe.

    Properties:
    - open_time strictly increasing by TIMEFRAME_MS[timeframe]
    - prices follow a seeded random walk (reproducible)
    - open_time of row i = start_open_time + i * step
    """
    rng = random.Random(seed)
    step = TIMEFRAME_MS[timeframe]
    rows: list[Row] = []
    price = start_price

    for i in range(n):
        open_time = start_open_time + i * step
        open_ = price
        # Small random moves for high/low/close
        change = rng.uniform(-2.0, 2.0)
        close = round(max(0.01, open_ + change), 4)
        high = round(max(open_, close) + rng.uniform(0, 1.0), 4)
        low = round(min(open_, close) - rng.uniform(0, 1.0), 4)
        volume = round(rng.uniform(100.0, 10_000.0), 4)
        rows.append((open_time, open_, high, low, close, volume))
        price = close  # next candle opens where this one closed

    return rows


# ---------------------------------------------------------------------------
# FakeExchange  (stub — fully implemented in Task C1)
# ---------------------------------------------------------------------------

class FakeExchange:
    """
    Minimal ccxt-like fake for unit tests.

    Usage:
        fake = FakeExchange(pages=[[row1, row2, ...], [...]])
        # each call to fetch_ohlcv returns the next page
    """

    def __init__(self, pages: list[list] | None = None, error: Exception | None = None):
        """
        pages : list of pages to return in sequence; [] means empty response.
        error : if set, raise this exception on every call.
        """
        self._pages = list(pages) if pages else []
        self._error = error
        self._call_count = 0

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: int | None = None,
        limit: int = 1000,
    ) -> list:
        self._call_count += 1
        if self._error is not None:
            raise self._error
        if not self._pages:
            return []
        return self._pages.pop(0)

    @property
    def call_count(self) -> int:
        return self._call_count
