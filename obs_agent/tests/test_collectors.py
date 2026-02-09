"""
Unit tests for monitoring collectors.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from obs_agent.collectors import (
    SystemMetrics,
    HealthChecker,
    LogTailer,
    MetricData,
    HealthCheckData,
    LogEntry
)


class TestSystemMetrics:
    """Test SystemMetrics collector"""

    def test_collect_returns_metric_data(self):
        """Should collect system metrics successfully"""
        collector = SystemMetrics(vps_name='test-vps', app_name='test-app')
        metrics = collector.collect()

        assert isinstance(metrics, MetricData)
        assert metrics.vps_name == 'test-vps'
        assert metrics.app_name == 'test-app'
        assert 0 <= metrics.cpu_percent <= 100
        assert 0 <= metrics.memory_percent <= 100
        assert metrics.memory_mb > 0
        assert 0 <= metrics.disk_percent <= 100
        assert metrics.disk_gb > 0
        assert metrics.load_avg_1m >= 0
        assert isinstance(metrics.timestamp, datetime)

    def test_collect_includes_load_averages(self):
        """Should include 1m, 5m, 15m load averages"""
        collector = SystemMetrics(vps_name='test-vps', app_name='test-app')
        metrics = collector.collect()

        assert hasattr(metrics, 'load_avg_1m')
        assert hasattr(metrics, 'load_avg_5m')
        assert hasattr(metrics, 'load_avg_15m')


class TestHealthChecker:
    """Test HealthChecker collector"""

    def test_successful_health_check(self):
        """Should record successful health check"""
        mock_response = Mock()
        mock_response.status_code = 200

        with patch('obs_agent.collectors.requests.get', return_value=mock_response):
            checker = HealthChecker(
                vps_name='test-vps',
                app_name='test-app',
                health_checks=[{'url': 'http://localhost:8000/health', 'timeout': 5}]
            )
            results = checker.check()

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, HealthCheckData)
        assert result.vps_name == 'test-vps'
        assert result.app_name == 'test-app'
        assert result.url == 'http://localhost:8000/health'
        assert result.status_code == 200
        assert result.success is True
        assert result.response_time_ms is not None
        assert result.response_time_ms > 0
        assert result.error_message is None

    def test_failed_health_check(self):
        """Should record failed health check (500 error)"""
        mock_response = Mock()
        mock_response.status_code = 500

        with patch('obs_agent.collectors.requests.get', return_value=mock_response):
            checker = HealthChecker(
                vps_name='test-vps',
                app_name='test-app',
                health_checks=[{'url': 'http://localhost:8000/health'}]
            )
            results = checker.check()

        result = results[0]
        assert result.status_code == 500
        assert result.success is False

    def test_timeout_health_check(self):
        """Should handle timeout gracefully"""
        with patch('obs_agent.collectors.requests.get', side_effect=requests.exceptions.Timeout):
            checker = HealthChecker(
                vps_name='test-vps',
                app_name='test-app',
                health_checks=[{'url': 'http://localhost:8000/health', 'timeout': 1}]
            )
            results = checker.check()

        result = results[0]
        assert result.success is False
        assert result.status_code is None
        assert result.response_time_ms is None
        assert 'Timeout' in result.error_message

    def test_connection_error_health_check(self):
        """Should handle connection errors"""
        with patch('obs_agent.collectors.requests.get', side_effect=requests.exceptions.ConnectionError('Connection refused')):
            checker = HealthChecker(
                vps_name='test-vps',
                app_name='test-app',
                health_checks=[{'url': 'http://localhost:8000/health'}]
            )
            results = checker.check()

        result = results[0]
        assert result.success is False
        assert 'Connection refused' in result.error_message

    def test_multiple_health_checks(self):
        """Should execute multiple health checks"""
        mock_response = Mock()
        mock_response.status_code = 200

        with patch('obs_agent.collectors.requests.get', return_value=mock_response):
            checker = HealthChecker(
                vps_name='test-vps',
                app_name='test-app',
                health_checks=[
                    {'url': 'http://localhost:8000/health'},
                    {'url': 'http://localhost:8000/status'},
                ]
            )
            results = checker.check()

        assert len(results) == 2
        assert results[0].url == 'http://localhost:8000/health'
        assert results[1].url == 'http://localhost:8000/status'


class TestLogTailer:
    """Test LogTailer collector"""

    def test_tail_empty_log_file(self):
        """Should handle empty log files"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name

        try:
            tailer = LogTailer(
                vps_name='test-vps',
                app_name='test-app',
                log_files=[log_file]
            )
            entries = tailer.tail()
            assert entries == []
        finally:
            Path(log_file).unlink()

    def test_tail_new_log_entries(self):
        """Should read new log entries"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name

        try:
            tailer = LogTailer(
                vps_name='test-vps',
                app_name='test-app',
                log_files=[log_file]
            )

            # First tail - empty
            entries = tailer.tail()
            assert entries == []

            # Write new log entry
            with open(log_file, 'a') as f:
                f.write('Test log message\n')

            # Second tail - should get new entry
            entries = tailer.tail()
            assert len(entries) == 1
            assert entries[0].message == 'Test log message'
            assert entries[0].vps_name == 'test-vps'
            assert entries[0].app_name == 'test-app'

            # Third tail - no new entries
            entries = tailer.tail()
            assert entries == []
        finally:
            Path(log_file).unlink()

    def test_tail_json_log_entries(self):
        """Should parse JSON formatted logs (logcore format)"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name

        try:
            tailer = LogTailer(
                vps_name='test-vps',
                app_name='test-app',
                log_files=[log_file]
            )

            # Write JSON log entry
            log_entry = {
                'timestamp': '2026-02-08T20:30:00Z',
                'level': 'ERROR',
                'logger': 'my_app',
                'message': 'Database connection failed',
                'context': {'retry_count': 3}
            }
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')

            entries = tailer.tail()
            assert len(entries) == 1
            entry = entries[0]
            assert entry.level == 'ERROR'
            assert entry.message == 'Database connection failed'
            assert entry.context == {'retry_count': 3}
        finally:
            Path(log_file).unlink()

    def test_tail_plain_text_logs(self):
        """Should handle plain text logs"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name
            f.write('Plain text log entry\n')

        try:
            tailer = LogTailer(
                vps_name='test-vps',
                app_name='test-app',
                log_files=[log_file]
            )

            entries = tailer.tail()
            assert len(entries) == 1
            assert entries[0].message == 'Plain text log entry'
            assert entries[0].level == 'INFO'  # Default level
        finally:
            Path(log_file).unlink()

    def test_tail_missing_log_file(self):
        """Should handle missing log files gracefully"""
        tailer = LogTailer(
            vps_name='test-vps',
            app_name='test-app',
            log_files=['/nonexistent/file.log']
        )

        # Should not raise exception
        entries = tailer.tail()
        assert entries == []

    def test_tail_multiple_log_files(self):
        """Should tail multiple log files"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f1, \
             tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f2:
            log_file1 = f1.name
            log_file2 = f2.name
            f1.write('Log from file 1\n')
            f2.write('Log from file 2\n')

        try:
            tailer = LogTailer(
                vps_name='test-vps',
                app_name='test-app',
                log_files=[log_file1, log_file2]
            )

            entries = tailer.tail()
            assert len(entries) == 2
            messages = {e.message for e in entries}
            assert 'Log from file 1' in messages
            assert 'Log from file 2' in messages
        finally:
            Path(log_file1).unlink()
            Path(log_file2).unlink()

    def test_tail_file_rotation(self):
        """Should handle log file rotation (file becomes smaller)"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name
            f.write('Original content with long line\n')  # 32 bytes

        try:
            tailer = LogTailer(
                vps_name='test-vps',
                app_name='test-app',
                log_files=[log_file]
            )

            # Read initial content
            entries = tailer.tail()
            assert len(entries) == 1

            # Simulate rotation: truncate and write shorter content
            with open(log_file, 'w') as f:
                f.write('New log\n')  # 8 bytes - smaller than 32

            # Should detect rotation and read from beginning
            entries = tailer.tail()
            assert len(entries) == 1
            assert entries[0].message == 'New log'
        finally:
            Path(log_file).unlink()
