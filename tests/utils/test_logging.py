"""Tests for the logging module.

This module contains tests for the logging utilities, including:
- JSON formatter
- Logging configuration
- Logging scopes
- Metrics collection
"""

import json
import logging
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

from agentic_kernel.utils.logging import (
    JsonFormatter,
    setup_logging,
    log_scope,
    get_logger,
    LogMetrics,
)


@pytest.fixture
def temp_log_file(tmp_path):
    """Fixture providing a temporary log file path."""
    return tmp_path / "test.log"


@pytest.fixture
def mock_time():
    """Fixture for mocking time.time() to return consistent values."""
    with patch("time.time") as mock:
        mock.return_value = 1234567890.0
        yield mock


@pytest.fixture
def mock_uuid():
    """Fixture for mocking uuid.uuid4() to return consistent values."""
    with patch("uuid.uuid4") as mock:
        mock.return_value = MagicMock(
            __str__=lambda _: "test-uuid"
        )
        yield mock


@pytest.fixture
def error_log_record():
    """Fixture providing a log record with exception information."""
    try:
        raise ValueError("Test error")
    except ValueError:
        return logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=True,
        )


class TestJsonFormatter:
    """Tests for the JsonFormatter class."""

    def test_format_basic_record(self):
        """Test basic record formatting."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = json.loads(formatter.format(record))

        assert result["logger"] == "test_logger"
        assert result["level"] == "INFO"
        assert result["path"] == "test.py"
        assert result["line"] == 42
        assert result["message"] == "Test message"
        assert "timestamp" in result

    def test_format_with_extra_fields(self):
        """Test formatting with extra fields."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.extra = {"user_id": "123", "action": "login"}

        result = json.loads(formatter.format(record))

        assert result["user_id"] == "123"
        assert result["action"] == "login"

    def test_format_with_exception(self, error_log_record):
        """Test formatting with exception information."""
        formatter = JsonFormatter()
        result = json.loads(formatter.format(error_log_record))

        assert "exc_info" in result
        assert "ValueError: Test error" in result["exc_info"]


class TestSetupLogging:
    """Tests for the setup_logging function."""

    def test_basic_setup(self):
        """Test basic logging setup with default values."""
        setup_logging()
        root_logger = logging.getLogger()

        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0], logging.StreamHandler)

    def test_setup_with_file(self, temp_log_file):
        """Test logging setup with file output."""
        setup_logging(log_file=temp_log_file)
        root_logger = logging.getLogger()

        assert len(root_logger.handlers) == 2
        assert any(isinstance(h, logging.FileHandler) for h in root_logger.handlers)
        assert os.path.exists(temp_log_file)

    def test_setup_with_json(self):
        """Test logging setup with JSON formatting."""
        setup_logging(use_json=True)
        root_logger = logging.getLogger()

        assert any(
            isinstance(h.formatter, JsonFormatter) for h in root_logger.handlers
        )

    def test_setup_with_custom_level(self):
        """Test logging setup with custom log level."""
        setup_logging(log_level=logging.DEBUG)
        root_logger = logging.getLogger()

        assert root_logger.level == logging.DEBUG


class TestLogScope:
    """Tests for the log_scope context manager."""

    def test_basic_scope(self, mock_time, mock_uuid, caplog):
        """Test basic scope functionality."""
        with log_scope("test_scope") as logger:
            logger.info("Test message")

        records = caplog.records
        assert len(records) == 3  # Enter, message, exit
        assert "Entering scope: test_scope" in records[0].message
        assert "Test message" in records[1].message
        assert "Exiting scope: test_scope" in records[2].message

    def test_scope_with_extra(self, mock_uuid, caplog):
        """Test scope with extra fields."""
        extra = {"user_id": "123"}
        with log_scope("test_scope", extra=extra) as logger:
            logger.info("Test message")

        for record in caplog.records:
            assert hasattr(record, "scope_id")
            assert record.scope_id == "test-uuid"
            if hasattr(record, "user_id"):
                assert record.user_id == "123"

    def test_scope_with_exception(self, caplog):
        """Test scope when an exception occurs."""
        with pytest.raises(ValueError):
            with log_scope("test_scope") as logger:
                raise ValueError("Test error")

        records = caplog.records
        assert len(records) == 3  # Enter, error, exit
        assert "Error in scope test_scope" in records[1].message
        assert "Test error" in records[1].exc_info[1].args[0]


class TestGetLogger:
    """Tests for the get_logger function."""

    def test_get_logger_basic(self):
        """Test basic logger creation."""
        logger = get_logger("test_module")

        assert logger.name == "test_module"
        assert logger.level == logging.INFO

    def test_get_logger_custom_level(self):
        """Test logger creation with custom level."""
        logger = get_logger("test_module", logging.DEBUG)

        assert logger.level == logging.DEBUG


class TestLogMetrics:
    """Tests for the LogMetrics class."""

    def test_increment_metric(self):
        """Test incrementing a metric."""
        metrics = LogMetrics("test_metrics")
        metrics.increment("counter")
        metrics.increment("counter", 2)

        assert metrics.metrics["counter"] == 3

    def test_timing_metric(self):
        """Test recording a timing metric."""
        metrics = LogMetrics("test_metrics")
        metrics.timing("duration", 1.5)

        assert metrics.metrics["duration"] == 1.5

    def test_gauge_metric(self):
        """Test setting a gauge metric."""
        metrics = LogMetrics("test_metrics")
        metrics.gauge("memory", 1024)

        assert metrics.metrics["memory"] == 1024

    def test_log_metrics(self, caplog):
        """Test logging collected metrics."""
        metrics = LogMetrics("test_metrics")
        metrics.increment("requests")
        metrics.timing("duration", 0.5)
        metrics.gauge("memory", 1024)

        metrics.log_metrics()

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert hasattr(record, "metrics")
        assert record.metrics == {
            "requests": 1,
            "duration": 0.5,
            "memory": 1024,
        } 