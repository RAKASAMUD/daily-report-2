"""Binance adapter — Tasks C1 + C2.

Thin seam between business logic and the ccxt exchange object.
All ccxt calls live here; tests inject a FakeExchange instead.
"""

import time as _time
from collections.abc import Callable
from typing import TypeVar

from data_layer.config import TIMEFRAME_MS
from data_layer.db import Row

# Max candles per ccxt request (Binance spot limit)
_PAGE_LIMIT = 1000

_T = TypeVar("_T")


def with_retry(
    fn: Callable[[], _T],
    attempts: int = 3,
    base_delay: float = 0.5,
    _sleep: Callable[[float], None] = _time.sleep,
) -> _T:
    """
    Call fn() up to `attempts` times, retrying on any exception.

    Between retries, sleeps for base_delay * 2^attempt seconds
    (exponential backoff: base, base*2, base*4, ...).
    Re-raises the last exception if all attempts are exhausted.

    Parameters
    ----------
    fn          : zero-argument callable to retry
    attempts    : maximum number of calls (default 3)
    base_delay  : initial sleep duration in seconds (default 0.5)
    _sleep      : injectable sleep function (use to avoid real sleeps in tests)
    """
    last_exc: Exception
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < attempts - 1:
                _sleep(base_delay * (2 ** attempt))
    raise last_exc


class BinanceAdapter:
    """
    Wraps a ccxt-like exchange object and exposes a single clean method
    that paginates forward and drops any unclosed trailing candle.

    Parameters
    ----------
    exchange : object
        A ccxt exchange instance (or FakeExchange in tests) that exposes
        ``fetch_ohlcv(symbol, timeframe, since, limit) -> list[list]``.
    """

    def __init__(self, exchange) -> None:
        self._exchange = exchange

    def fetch_closed_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since_ms: int,
        now_ms: int,
    ) -> list[Row]:
        """
        Paginate forward from since_ms up to now_ms.

        Converts ccxt's [ts, o, h, l, c, v] lists to Row tuples.
        Drops the final candle if it is not yet closed:
            open_time + TIMEFRAME_MS[tf] > now_ms
        """
        tf_ms = TIMEFRAME_MS[timeframe]
        all_rows: list[Row] = []
        since = since_ms

        while True:
            raw_page = with_retry(
                lambda: self._exchange.fetch_ohlcv(
                    symbol, timeframe, since=since, limit=_PAGE_LIMIT
                )
            )
            if not raw_page:
                # Empty page → no more data
                break

            for item in raw_page:
                open_time = int(item[0])
                row: Row = (
                    open_time,
                    float(item[1]),  # open
                    float(item[2]),  # high
                    float(item[3]),  # low
                    float(item[4]),  # close
                    float(item[5]),  # volume
                )
                all_rows.append(row)

            # Advance since to one step past the last fetched open_time
            since = raw_page[-1][0] + tf_ms

        # Drop the last candle if it is not yet closed
        if all_rows:
            last_open_time = all_rows[-1][0]
            if last_open_time + tf_ms > now_ms:
                all_rows.pop()

        return all_rows
