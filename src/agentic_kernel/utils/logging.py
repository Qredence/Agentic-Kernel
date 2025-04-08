"""Logging utilities and configuration.

This module provides a centralized logging configuration and utilities for the
agentic-kernel package. It includes structured logging formatters, custom handlers,
and context managers for logging scopes.

Key features:
    1. Structured JSON logging
    2. Custom formatters and handlers
    3. Context managers for logging scopes
    4. Log level management
    5. Performance monitoring

Example:
    .. code-block:: python

        from agentic_kernel.utils.logging import setup_logging, log_scope

        # Setup logging with custom configuration
        setup_logging(log_level="INFO", log_file="app.log")

        # Use context manager for logging scope
        with log_scope("data_processing") as logger:
            logger.info("Processing started", extra={"batch_size": 100})
            # ... processing logic ...
            logger.info("Processing completed", extra={"items_processed": 100})
"""

import json
import logging
import logging.config
import os
import sys
import time
import types
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

# Default logging format for structured logging
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# JSON logging formatter for structured logs
class JsonFormatter(logging.Formatter):
    """Format log records as JSON strings.

    This formatter converts log records into JSON format, with customizable field mapping
    and default fields. It handles both standard log record attributes and custom fields
    added through the 'extra' parameter.

    Args:
        default_fields: Dictionary mapping output field names to record attribute names.
        field_map: Additional dictionary for renaming fields in the output.

    Example:
        .. code-block:: python

            formatter = JsonFormatter(
                default_fields={'event_time': 'created'},
                field_map={'levelname': 'severity'}
            )
    """

    def __init__(
        self,
        default_fields: Optional[Dict[str, str]] = None,
        field_map: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialize the JSON formatter with field mappings."""
        super().__init__()
        self.default_fields = default_fields or {
            "timestamp": "created",
            "level": "levelname",
            "name": "name",
        }
        self.field_map = field_map or {}

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string.

        Args:
            record: The log record to format.

        Returns:
            str: JSON-formatted log record.
        """
        # Create base record dictionary with mapped default fields
        record_dict = {}
        
        # Process default fields first
        for output_field, record_field in self.default_fields.items():
            if hasattr(record, record_field):
                record_dict[output_field] = getattr(record, record_field)

        # Add the formatted message
        record_dict['message'] = self.formatMessage(record)

        # Add any extra fields from the record
        if hasattr(record, 'extra_fields'):
            record_dict.update(record.extra_fields)

        # Handle exception info if present
        if record.exc_info:
            # Only process if exc_info is a tuple (type, value, traceback)
            if isinstance(record.exc_info, tuple):
                formatted = self.formatException(record.exc_info)
                record_dict['exc_info'] = formatted

        # Remove internal fields that we don't want in the output
        for key in ('msg', 'args', 'exc_info', 'exc_text'):
            record_dict.pop(key, None)

        # Apply any additional field mapping
        for old_key, new_key in self.field_map.items():
            if old_key in record_dict:
                record_dict[new_key] = record_dict.pop(old_key)

        return json.dumps(record_dict)


def setup_logging(
    log_level: Union[str, int] = logging.INFO,
    log_file: Optional[Union[str, Path]] = None,
    use_json: bool = False,
    log_dir: Optional[Union[str, Path]] = None,
) -> None:
    """Set up logging configuration.

    Args:
        log_level: The logging level to use.
        log_file: Optional path to log file.
        use_json: Whether to use JSON formatting.
        log_dir: Optional directory for log files.

    Example:
        .. code-block:: python

            # Basic setup with console output
            setup_logging(log_level="INFO")

            # Setup with file output and JSON formatting
            setup_logging(
                log_level="DEBUG",
                log_file="app.log",
                use_json=True
            )
    """
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {"format": DEFAULT_FORMAT},
            "json": {"()": JsonFormatter},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json" if use_json else "standard",
                "stream": sys.stdout,
            }
        },
        "root": {"level": log_level, "handlers": ["console"]},
    }

    if log_file:
        if log_dir:
            log_path = Path(log_dir) / log_file
            log_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            log_path = Path(log_file)

        config["handlers"]["file"] = {
            "class": "logging.FileHandler",
            "formatter": "json" if use_json else "standard",
            "filename": str(log_path),
            "mode": "a",
        }
        config["root"]["handlers"].append("file")

    logging.config.dictConfig(config)


@contextmanager
def log_scope(
    name: str,
    level: Union[str, int] = logging.INFO,
    extra: Optional[Dict[str, Any]] = None,
):
    """Context manager for logging scope.

    Args:
        name: Name of the logging scope.
        level: Logging level for this scope.
        extra: Optional extra fields to include in logs.

    Yields:
        logging.Logger: Logger instance for the scope.

    Example:
        .. code-block:: python

            with log_scope("data_processing", extra={"batch_id": 123}) as logger:
                logger.info("Starting processing")
                # ... processing logic ...
                logger.info("Processing complete")
    """
    logger = logging.getLogger(name)
    scope_id = str(uuid.uuid4())
    start_time = time.time()

    extra = extra or {}
    extra.update({"scope_id": scope_id})

    logger.log(level, f"Entering scope: {name}", extra=extra)

    try:
        yield logger
    except Exception as e:
        logger.exception(
            f"Error in scope {name}",
            extra={**extra, "error": str(e), "duration": time.time() - start_time},
        )
        raise
    finally:
        logger.log(
            level,
            f"Exiting scope: {name}",
            extra={**extra, "duration": time.time() - start_time},
        )


def get_logger(
    name: str, level: Union[str, int] = logging.INFO
) -> logging.Logger:
    """Get a logger with the specified name and level.

    Args:
        name: Name for the logger.
        level: Logging level to use.

    Returns:
        logging.Logger: Configured logger instance.

    Example:
        .. code-block:: python

            logger = get_logger("my_module", "DEBUG")
            logger.debug("Detailed debug information")
            logger.info("General information")
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger


class LogMetrics:
    """Utility class for collecting and logging metrics.

    This class provides methods for tracking and logging performance metrics
    and other measurements throughout the application.

    Example:
        .. code-block:: python

            metrics = LogMetrics("task_processor")
            metrics.increment("items_processed")
            metrics.timing("processing_time", 1.5)
            metrics.log_metrics()  # Logs all collected metrics
    """

    def __init__(self, name: str):
        """Initialize the metrics collector.

        Args:
            name: Name for the metrics collector.
        """
        self.name = name
        self.logger = get_logger(f"metrics.{name}")
        self.metrics: Dict[str, Any] = {}

    def increment(self, metric: str, value: int = 1) -> None:
        """Increment a counter metric.

        Args:
            metric: Name of the metric.
            value: Value to increment by.
        """
        self.metrics[metric] = self.metrics.get(metric, 0) + value

    def timing(self, metric: str, value: float) -> None:
        """Record a timing metric.

        Args:
            metric: Name of the metric.
            value: Timing value in seconds.
        """
        self.metrics[metric] = value

    def gauge(self, metric: str, value: float) -> None:
        """Set a gauge metric.

        Args:
            metric: Name of the metric.
            value: Current value.
        """
        self.metrics[metric] = value

    def log_metrics(self, level: Union[str, int] = logging.INFO) -> None:
        """Log all collected metrics.

        Args:
            level: Logging level to use.
        """
        self.logger.log(level, "Metrics", extra={"metrics": self.metrics.copy()})
        self.metrics.clear() 