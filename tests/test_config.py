"""Tests for data_layer.config — Task A1."""

from data_layer.config import SYMBOLS, TIMEFRAMES, TIMEFRAME_MS, BACKFILL_DAYS, DB_PATH


class TestSymbols:
    def test_symbols_is_list(self):
        assert isinstance(SYMBOLS, list)

    def test_all_symbols_are_usdt_pairs(self):
        for s in SYMBOLS:
            assert s.endswith("/USDT"), f"{s} is not a */USDT pair"

    def test_expected_symbols_present(self):
        expected = {"BTC/USDT", "ETH/USDT", "SOL/USDT", "SUI/USDT", "AVAX/USDT"}
        assert set(SYMBOLS) == expected


class TestTimeframes:
    def test_timeframes_is_list(self):
        assert isinstance(TIMEFRAMES, list)

    def test_expected_timeframes(self):
        assert TIMEFRAMES == ["5m", "15m", "1h", "4h"]


class TestTimeframeMs:
    def test_every_timeframe_has_ms_entry(self):
        for tf in TIMEFRAMES:
            assert tf in TIMEFRAME_MS, f"{tf} missing from TIMEFRAME_MS"

    def test_5m_duration(self):
        assert TIMEFRAME_MS["5m"] == 300_000

    def test_15m_duration(self):
        assert TIMEFRAME_MS["15m"] == 900_000

    def test_1h_duration(self):
        assert TIMEFRAME_MS["1h"] == 3_600_000

    def test_4h_duration(self):
        assert TIMEFRAME_MS["4h"] == 14_400_000


class TestBackfillDays:
    def test_backfill_days_value(self):
        assert BACKFILL_DAYS == 730


class TestDbPath:
    def test_db_path_value(self):
        assert DB_PATH == "data/candles.db"
