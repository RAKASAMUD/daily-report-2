"""Tests for data_layer.logging_setup — Task D3: logging setup idempotency."""

import logging
import pytest

from data_layer.logging_setup import setup_logging


class TestSetupLogging:
    def teardown_method(self):
        """Remove all handlers added during each test to keep the test suite clean."""
        root = logging.getLogger("data_layer")
        root.handlers.clear()

    def test_adds_handlers(self, tmp_path):
        """After setup_logging, the data_layer logger has at least one handler."""
        logfile = str(tmp_path / "test.log")
        setup_logging(logfile=logfile)
        logger = logging.getLogger("data_layer")
        assert len(logger.handlers) >= 1

    def test_creates_file_handler(self, tmp_path):
        """A FileHandler writing to the given logfile is attached."""
        logfile = str(tmp_path / "test.log")
        setup_logging(logfile=logfile)
        logger = logging.getLogger("data_layer")
        file_handlers = [
            h for h in logger.handlers if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) >= 1
        assert file_handlers[0].baseFilename == logfile

    def test_creates_stream_handler(self, tmp_path):
        """A StreamHandler (stdout/stderr) is also attached."""
        logfile = str(tmp_path / "test.log")
        setup_logging(logfile=logfile)
        logger = logging.getLogger("data_layer")
        stream_handlers = [
            h for h in logger.handlers if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert len(stream_handlers) >= 1

    def test_idempotent_no_duplicate_handlers(self, tmp_path):
        """Calling setup_logging twice must not add duplicate handlers."""
        logfile = str(tmp_path / "test.log")
        setup_logging(logfile=logfile)
        first_count = len(logging.getLogger("data_layer").handlers)

        setup_logging(logfile=logfile)
        second_count = len(logging.getLogger("data_layer").handlers)

        assert first_count == second_count, (
            f"Duplicate handlers detected: {first_count} → {second_count}"
        )

    def test_level_is_info_or_lower(self, tmp_path):
        """Logger level must be INFO or lower so INFO messages are captured."""
        logfile = str(tmp_path / "test.log")
        setup_logging(logfile=logfile)
        logger = logging.getLogger("data_layer")
        assert logger.level <= logging.INFO

    def test_log_file_created(self, tmp_path):
        """The log file is actually created after setup_logging is called."""
        logfile = str(tmp_path / "subdir" / "app.log")
        setup_logging(logfile=logfile)
        logger = logging.getLogger("data_layer")
        logger.info("test message")
        # Flush all handlers
        for h in logger.handlers:
            h.flush()
        import os
        assert os.path.exists(logfile)
