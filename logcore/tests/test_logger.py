"""
Unit tests for LogCore logging library.
"""

import json
import logging
import tempfile
from pathlib import Path

import pytest

from logcore.logger import JSONFormatter, get_logger, validate_log_format


class TestJSONFormatter:
    """Test JSONFormatter"""

    def test_format_basic_log(self):
        """Should format log as JSON with required fields"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert 'timestamp' in data
        assert data['level'] == 'INFO'
        assert data['logger'] == 'test_logger'
        assert data['message'] == 'Test message'

    def test_format_with_context(self):
        """Should include context from extra fields"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='User action',
            args=(),
            exc_info=None
        )
        record.context = {'user_id': 123, 'action': 'login'}

        output = formatter.format(record)
        data = json.loads(output)

        assert 'context' in data
        assert data['context']['user_id'] == 123
        assert data['context']['action'] == 'login'

    def test_format_with_exception(self):
        """Should include exception info"""
        formatter = JSONFormatter()

        try:
            raise ValueError('Test error')
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name='test_logger',
            level=logging.ERROR,
            pathname='test.py',
            lineno=42,
            msg='Error occurred',
            args=(),
            exc_info=exc_info
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert 'exception' in data
        assert data['exception']['type'] == 'ValueError'
        assert data['exception']['message'] == 'Test error'
        assert 'traceback' in data['exception']

    def test_format_debug_includes_source(self):
        """Should include source location in debug mode"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test_logger',
            level=logging.DEBUG,
            pathname='/path/to/test.py',
            lineno=42,
            msg='Debug message',
            args=(),
            exc_info=None,
            func='test_function'
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert 'source' in data
        assert data['source']['file'] == '/path/to/test.py'
        assert data['source']['line'] == 42
        assert data['source']['function'] == 'test_function'

    def test_format_info_no_source(self):
        """Should not include source location for INFO and above"""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='/path/to/test.py',
            lineno=42,
            msg='Info message',
            args=(),
            exc_info=None
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert 'source' not in data


class TestGetLogger:
    """Test get_logger function"""

    def test_get_logger_returns_logger(self):
        """Should return configured logger instance"""
        logger = get_logger('test_app')

        assert isinstance(logger, logging.Logger)
        assert logger.name == 'test_app'
        assert logger.level == logging.INFO

    def test_get_logger_with_custom_level(self):
        """Should set custom log level"""
        logger = get_logger('test_app', level=logging.DEBUG)

        assert logger.level == logging.DEBUG

    def test_get_logger_json_output(self, caplog):
        """Should output JSON formatted logs"""
        import io
        import sys

        # Capture handler output directly
        logger = logging.getLogger('test_app_json_unique')
        logger.setLevel(logging.INFO)
        logger.handlers.clear()  # Clear any existing handlers

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

        logger.info('Test message')

        output = stream.getvalue()
        data = json.loads(output)

        assert data['level'] == 'INFO'
        assert data['message'] == 'Test message'
        assert data['logger'] == 'test_app_json_unique'

    def test_get_logger_with_file(self):
        """Should write to log file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name

        try:
            # Create unique logger name to avoid handler pollution
            import uuid
            logger_name = f'test_file_{uuid.uuid4().hex[:8]}'

            logger = get_logger(logger_name, log_file=log_file)
            logger.info('File log message')

            # Flush handlers to ensure write
            for handler in logger.handlers:
                handler.flush()

            # Read log file
            content = Path(log_file).read_text()

            # File should have content
            assert len(content) > 0, f"Log file is empty"

            data = json.loads(content.strip())
            assert data['message'] == 'File log message'
        finally:
            Path(log_file).unlink()

    def test_get_logger_with_context(self):
        """Should support context in extra parameter"""
        import io

        logger = logging.getLogger('test_app_context_unique')
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

        logger.info('User action', extra={'context': {'user_id': 456}})

        output = stream.getvalue()
        data = json.loads(output)

        assert data['message'] == 'User action'
        assert data['context']['user_id'] == 456

    def test_get_logger_no_duplicate_handlers(self):
        """Should not add duplicate handlers"""
        logger1 = get_logger('test_app_dup')
        handlers_count1 = len(logger1.handlers)

        logger2 = get_logger('test_app_dup')
        handlers_count2 = len(logger2.handlers)

        assert logger1 is logger2
        assert handlers_count1 == handlers_count2

    def test_get_logger_plain_text(self):
        """Should support plain text format"""
        import io

        logger = logging.getLogger('test_app_plain_unique')
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

        logger.info('Plain text message')

        output = stream.getvalue()

        assert 'Plain text message' in output
        assert 'INFO' in output
        # Should NOT be JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(output)


class TestValidateLogFormat:
    """Test validate_log_format function"""

    def test_validate_valid_json_log(self):
        """Should validate correct JSON log format"""
        log_line = json.dumps({
            'timestamp': '2026-02-08T20:30:00Z',
            'level': 'INFO',
            'logger': 'my_app',
            'message': 'Test message'
        })

        assert validate_log_format(log_line) is True

    def test_validate_missing_required_field(self):
        """Should reject logs missing required fields"""
        log_line = json.dumps({
            'timestamp': '2026-02-08T20:30:00Z',
            'level': 'INFO',
            # Missing 'logger' and 'message'
        })

        assert validate_log_format(log_line) is False

    def test_validate_invalid_level(self):
        """Should reject logs with invalid level"""
        log_line = json.dumps({
            'timestamp': '2026-02-08T20:30:00Z',
            'level': 'INVALID',
            'logger': 'my_app',
            'message': 'Test message'
        })

        assert validate_log_format(log_line) is False

    def test_validate_not_json(self):
        """Should reject non-JSON strings"""
        log_line = 'Plain text log entry'

        assert validate_log_format(log_line) is False

    def test_validate_with_optional_context(self):
        """Should accept logs with optional context field"""
        log_line = json.dumps({
            'timestamp': '2026-02-08T20:30:00Z',
            'level': 'ERROR',
            'logger': 'my_app',
            'message': 'Error occurred',
            'context': {'error_code': 500}
        })

        assert validate_log_format(log_line) is True
