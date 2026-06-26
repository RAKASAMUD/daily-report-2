"""Tests for data_layer.db — Task A2: schema and connection."""

import sqlite3
import tempfile
import os

import pytest

from data_layer.db import connect, init_schema


class TestConnect:
    def test_returns_connection(self):
        conn = connect(":memory:")
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_wal_mode_on_file_db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            conn = connect(db_path)
            row = conn.execute("PRAGMA journal_mode").fetchone()
            assert row[0] == "wal"
            conn.close()
        finally:
            os.unlink(db_path)


class TestInitSchema:
    def _get_conn(self):
        conn = connect(":memory:")
        return conn

    def test_candles_table_exists(self):
        conn = self._get_conn()
        init_schema(conn)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='candles'"
        ).fetchone()
        assert row is not None, "Table 'candles' does not exist"
        conn.close()

    def test_candles_has_8_columns(self):
        conn = self._get_conn()
        init_schema(conn)
        cols = conn.execute("PRAGMA table_info(candles)").fetchall()
        col_names = [c[1] for c in cols]
        expected = ["symbol", "timeframe", "open_time", "open", "high", "low", "close", "volume"]
        assert col_names == expected, f"Expected {expected}, got {col_names}"
        conn.close()

    def test_init_schema_twice_does_not_error(self):
        conn = self._get_conn()
        init_schema(conn)
        # calling again should not raise
        init_schema(conn)
        conn.close()

    def test_primary_key_columns(self):
        conn = self._get_conn()
        init_schema(conn)
        cols = conn.execute("PRAGMA table_info(candles)").fetchall()
        # pk field is index 5 in PRAGMA table_info: nonzero means it's part of PK
        pk_cols = [c[1] for c in cols if c[5] != 0]
        assert set(pk_cols) == {"symbol", "timeframe", "open_time"}
        conn.close()
