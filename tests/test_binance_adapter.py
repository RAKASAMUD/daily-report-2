"""Tests for data_layer.binance — Task C1: BinanceAdapter + FakeExchange."""

import pytest

from data_layer.binance import BinanceAdapter
from data_layer.testkit import FakeExchange, random_walk_candles
from data_layer.config import TIMEFRAME_MS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ccxt_row(open_time: int, o: float, h: float, l: float, c: float, v: float) -> list:
    """ccxt returns [timestamp, open, high, low, close, volume]."""
    return [open_time, o, h, l, c, v]


def _make_ccxt_rows(n: int, start_ms: int, tf: str) -> list[list]:
    """Generate n ccxt-format rows, strictly increasing by tf step."""
    step = TIMEFRAME_MS[tf]
    return [
        _ccxt_row(start_ms + i * step, 100.0 + i, 105.0 + i, 95.0 + i, 102.0 + i, 1000.0 + i)
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Tests: normal conversion
# ---------------------------------------------------------------------------

class TestFetchClosedOhlcv:
    def test_normal_page_correct_field_order_and_types(self):
        """Rows are converted from ccxt format to Row tuple with correct types."""
        tf = "5m"
        now_ms = 1_700_000_900_000  # well past close of 3rd candle (start + 3*300_000)
        ccxt_rows = _make_ccxt_rows(3, 1_700_000_000_000, tf)

        fake = FakeExchange(pages=[ccxt_rows, []])  # second call returns empty → stops
        adapter = BinanceAdapter(fake)
        result = adapter.fetch_closed_ohlcv("BTC/USDT", tf, 1_700_000_000_000, now_ms)

        assert len(result) == 3
        for row in result:
            open_time, open_, high, low, close, volume = row
            assert isinstance(open_time, int)
            assert isinstance(open_, float)
            assert isinstance(high, float)
            assert isinstance(low, float)
            assert isinstance(close, float)
            assert isinstance(volume, float)

    def test_field_values_match_ccxt_input(self):
        """Each Row field maps correctly from the ccxt [ts,o,h,l,c,v] format."""
        tf = "5m"
        now_ms = 1_700_000_600_000
        raw = [1_700_000_000_000, 123.4, 130.0, 120.0, 127.5, 9999.9]
        fake = FakeExchange(pages=[[raw], []])
        adapter = BinanceAdapter(fake)
        result = adapter.fetch_closed_ohlcv("BTC/USDT", tf, 1_700_000_000_000, now_ms)

        assert len(result) == 1
        t, o, h, l, c, v = result[0]
        assert t == 1_700_000_000_000
        assert o == 123.4
        assert h == 130.0
        assert l == 120.0
        assert c == 127.5
        assert v == 9999.9

    # -----------------------------------------------------------------------
    # Tests: unclosed candle is dropped
    # -----------------------------------------------------------------------

    def test_last_unclosed_candle_is_excluded(self):
        """
        If the last candle's open_time + tf_ms > now_ms, it is not yet closed
        and must be dropped.
        """
        tf = "5m"
        tf_ms = TIMEFRAME_MS[tf]
        # 3 candles: open_times at T, T+step, T+2*step
        start = 1_700_000_000_000
        ccxt_rows = _make_ccxt_rows(3, start, tf)
        last_open_time = start + 2 * tf_ms

        # now_ms is inside the last candle (not closed yet)
        now_ms = last_open_time + tf_ms - 1

        fake = FakeExchange(pages=[ccxt_rows, []])
        adapter = BinanceAdapter(fake)
        result = adapter.fetch_closed_ohlcv("BTC/USDT", tf, start, now_ms)

        # Only the first two candles are closed
        assert len(result) == 2
        assert result[-1][0] == start + tf_ms  # second candle open_time

    def test_prior_candle_kept_when_last_unclosed(self):
        """The candle immediately before the unclosed one is retained."""
        tf = "15m"
        tf_ms = TIMEFRAME_MS[tf]
        start = 1_700_000_000_000
        ccxt_rows = _make_ccxt_rows(4, start, tf)
        last_open_time = start + 3 * tf_ms

        # now_ms is inside the last candle
        now_ms = last_open_time + 1

        fake = FakeExchange(pages=[ccxt_rows, []])
        adapter = BinanceAdapter(fake)
        result = adapter.fetch_closed_ohlcv("BTC/USDT", tf, start, now_ms)

        assert len(result) == 3
        assert result[-1][0] == start + 2 * tf_ms

    def test_exactly_closed_candle_is_kept(self):
        """A candle whose open_time + tf_ms == now_ms is exactly closed and kept."""
        tf = "5m"
        tf_ms = TIMEFRAME_MS[tf]
        start = 1_700_000_000_000
        ccxt_rows = _make_ccxt_rows(2, start, tf)
        last_open_time = start + tf_ms

        # now_ms is exactly the close time of the last candle
        now_ms = last_open_time + tf_ms

        fake = FakeExchange(pages=[ccxt_rows, []])
        adapter = BinanceAdapter(fake)
        result = adapter.fetch_closed_ohlcv("BTC/USDT", tf, start, now_ms)

        assert len(result) == 2  # both candles are closed

    # -----------------------------------------------------------------------
    # Tests: edge cases
    # -----------------------------------------------------------------------

    def test_empty_response_returns_empty_list(self):
        fake = FakeExchange(pages=[[]])
        adapter = BinanceAdapter(fake)
        result = adapter.fetch_closed_ohlcv("BTC/USDT", "5m", 1_700_000_000_000, 1_700_001_000_000)
        assert result == []

    def test_pagination_fetches_multiple_pages(self):
        """When first page is non-empty, adapter fetches next page too."""
        tf = "5m"
        start = 1_700_000_000_000
        page1 = _make_ccxt_rows(3, start, tf)
        page2 = _make_ccxt_rows(3, start + 3 * TIMEFRAME_MS[tf], tf)
        now_ms = start + 7 * TIMEFRAME_MS[tf]  # all 6 candles are closed

        fake = FakeExchange(pages=[page1, page2, []])
        adapter = BinanceAdapter(fake)
        result = adapter.fetch_closed_ohlcv("BTC/USDT", tf, start, now_ms)

        assert len(result) == 6


# ---------------------------------------------------------------------------
# Tests: random_walk_candles determinism (C1 spec)
# ---------------------------------------------------------------------------

class TestRandomWalkCandles:
    def test_same_seed_produces_identical_output(self):
        rows_a = random_walk_candles(1_700_000_000_000, "5m", 30, seed=1)
        rows_b = random_walk_candles(1_700_000_000_000, "5m", 30, seed=1)
        assert rows_a == rows_b

    def test_different_seeds_produce_different_prices(self):
        rows_a = random_walk_candles(1_700_000_000_000, "5m", 10, seed=1)
        rows_b = random_walk_candles(1_700_000_000_000, "5m", 10, seed=99)
        prices_a = [r[4] for r in rows_a]  # close prices
        prices_b = [r[4] for r in rows_b]
        assert prices_a != prices_b

    def test_open_times_strictly_increasing(self):
        rows = random_walk_candles(1_700_000_000_000, "1h", 20, seed=7)
        times = [r[0] for r in rows]
        assert times == sorted(times)
        assert len(set(times)) == len(times)  # no duplicates


# ---------------------------------------------------------------------------
# Tests: with_retry — Task C2
# ---------------------------------------------------------------------------

class TestWithRetry:
    def test_fails_twice_then_succeeds_returns_result(self):
        """A callable that fails twice then succeeds must return the success value."""
        from data_layer.binance import with_retry

        call_count = 0
        sleep_calls = []

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return "ok"

        result = with_retry(flaky, attempts=3, base_delay=1.0, _sleep=sleep_calls.append)
        assert result == "ok"
        assert call_count == 3

    def test_fail_twice_sleeps_with_backoff(self):
        """Sleep durations grow exponentially: base, base*2, ..."""
        from data_layer.binance import with_retry

        call_count = 0
        sleep_calls = []

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return "ok"

        with_retry(flaky, attempts=3, base_delay=0.5, _sleep=sleep_calls.append)
        # Two failures → two sleeps: 0.5, 1.0
        assert len(sleep_calls) == 2
        assert sleep_calls[0] == pytest.approx(0.5)
        assert sleep_calls[1] == pytest.approx(1.0)

    def test_always_fails_raises_after_attempts(self):
        """If all attempts fail, the original exception is re-raised."""
        from data_layer.binance import with_retry

        call_count = 0

        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("always bad")

        with pytest.raises(ValueError, match="always bad"):
            with_retry(always_fail, attempts=3, base_delay=0.0, _sleep=lambda _: None)

        assert call_count == 3

    def test_succeeds_first_try_no_sleep(self):
        """If the first call succeeds, sleep is never called."""
        from data_layer.binance import with_retry

        sleep_calls = []

        result = with_retry(lambda: 42, attempts=3, base_delay=1.0, _sleep=sleep_calls.append)
        assert result == 42
        assert sleep_calls == []

    def test_attempts_1_raises_immediately(self):
        """With attempts=1, a single failure propagates immediately."""
        from data_layer.binance import with_retry

        with pytest.raises(RuntimeError):
            with_retry(
                lambda: (_ for _ in ()).throw(RuntimeError("boom")),
                attempts=1,
                base_delay=0.0,
                _sleep=lambda _: None,
            )
