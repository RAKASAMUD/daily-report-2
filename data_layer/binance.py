"""Binance adapter — Task C1.

Thin seam between business logic and the ccxt exchange object.
All ccxt calls live here; tests inject a FakeExchange instead.
"""

from data_layer.config import TIMEFRAME_MS
from data_layer.db import Row

# Max candles per ccxt request (Binance spot limit)
_PAGE_LIMIT = 1000


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
            raw_page = self._exchange.fetch_ohlcv(
                symbol, timeframe, since=since, limit=_PAGE_LIMIT
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
