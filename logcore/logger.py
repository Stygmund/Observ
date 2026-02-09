"""
LogCore: Standardized JSON logging library with validation.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs.

    Output format:
    {
        "timestamp": "2026-02-08T20:30:00.123456Z",
        "level": "INFO",
        "logger": "my_app.module",
        "message": "User logged in",
        "context": {...}  # Optional extra fields
    }
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        # Base log structure
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        # Add context if present (from logger.info(..., extra={'context': {...}}))
        if hasattr(record, 'context') and record.context:
            log_data['context'] = record.context

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }

        # Add source location in debug mode
        if record.levelno <= logging.DEBUG:
            log_data['source'] = {
                'file': record.pathname,
                'line': record.lineno,
                'function': record.funcName
            }

        return json.dumps(log_data, default=str)


def get_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    use_json: bool = True
) -> logging.Logger:
    """
    Get a pre-configured logger instance.

    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: INFO)
        log_file: Optional file path for file handler
        use_json: Use JSON formatter (default: True)

    Returns:
        Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("User action", extra={'context': {'user_id': 123}})
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Check if we already have handlers to avoid duplicates
    has_console_handler = any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
                              for h in logger.handlers)
    has_file_handler = any(isinstance(h, logging.FileHandler) and h.baseFilename == log_file
                           for h in logger.handlers) if log_file else False

    # Console handler
    if not has_console_handler:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        if use_json:
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )

        logger.addHandler(console_handler)

    # File handler (optional)
    if log_file and not has_file_handler:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)

        if use_json:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )

        logger.addHandler(file_handler)

    return logger


def validate_log_format(log_line: str) -> bool:
    """
    Validate that a log line is properly formatted JSON.

    Args:
        log_line: Log line to validate

    Returns:
        True if valid JSON with required fields, False otherwise
    """
    try:
        data = json.loads(log_line)

        # Check required fields
        required_fields = ['timestamp', 'level', 'logger', 'message']
        if not all(field in data for field in required_fields):
            return False

        # Validate level is a valid log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if data['level'] not in valid_levels:
            return False

        return True

    except (json.JSONDecodeError, TypeError):
        return False
