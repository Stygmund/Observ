"""
Collectors for system metrics, health checks, and log tailing.
"""

import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any

import psutil
import requests


@dataclass
class MetricData:
    """System metrics snapshot"""
    timestamp: datetime
    vps_name: str
    app_name: str
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_percent: float
    disk_gb: float
    load_avg_1m: float
    load_avg_5m: float
    load_avg_15m: float


@dataclass
class HealthCheckData:
    """Health check result"""
    timestamp: datetime
    vps_name: str
    app_name: str
    url: str
    status_code: Optional[int]
    response_time_ms: Optional[float]
    success: bool
    error_message: Optional[str] = None


@dataclass
class LogEntry:
    """Parsed log entry"""
    timestamp: datetime
    vps_name: str
    app_name: str
    level: str
    message: str
    context: Optional[Dict[str, Any]] = None


class SystemMetrics:
    """Collects system-level metrics using psutil"""

    def __init__(self, vps_name: str, app_name: str):
        self.vps_name = vps_name
        self.app_name = app_name

    def collect(self) -> MetricData:
        """Collect current system metrics"""
        # CPU percentage (1 second average)
        cpu_percent = psutil.cpu_percent(interval=1)

        # Memory
        mem = psutil.virtual_memory()
        memory_percent = mem.percent
        memory_mb = mem.used / (1024 * 1024)

        # Disk (root partition)
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_gb = disk.used / (1024 * 1024 * 1024)

        # Load average
        load_avg = psutil.getloadavg()

        return MetricData(
            timestamp=datetime.utcnow(),
            vps_name=self.vps_name,
            app_name=self.app_name,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_mb=memory_mb,
            disk_percent=disk_percent,
            disk_gb=disk_gb,
            load_avg_1m=load_avg[0],
            load_avg_5m=load_avg[1],
            load_avg_15m=load_avg[2]
        )


class HealthChecker:
    """Performs HTTP health checks"""

    def __init__(self, vps_name: str, app_name: str, health_checks: List[Dict[str, Any]]):
        self.vps_name = vps_name
        self.app_name = app_name
        self.health_checks = health_checks

    def check(self) -> List[HealthCheckData]:
        """Execute all configured health checks"""
        results = []

        for check_config in self.health_checks:
            url = check_config['url']
            timeout = check_config.get('timeout', 5)

            timestamp = datetime.utcnow()
            start_time = time.time()

            try:
                response = requests.get(url, timeout=timeout)
                response_time_ms = (time.time() - start_time) * 1000

                results.append(HealthCheckData(
                    timestamp=timestamp,
                    vps_name=self.vps_name,
                    app_name=self.app_name,
                    url=url,
                    status_code=response.status_code,
                    response_time_ms=response_time_ms,
                    success=(200 <= response.status_code < 400),
                    error_message=None
                ))
            except requests.exceptions.Timeout:
                results.append(HealthCheckData(
                    timestamp=timestamp,
                    vps_name=self.vps_name,
                    app_name=self.app_name,
                    url=url,
                    status_code=None,
                    response_time_ms=None,
                    success=False,
                    error_message=f"Timeout after {timeout}s"
                ))
            except Exception as e:
                results.append(HealthCheckData(
                    timestamp=timestamp,
                    vps_name=self.vps_name,
                    app_name=self.app_name,
                    url=url,
                    status_code=None,
                    response_time_ms=None,
                    success=False,
                    error_message=str(e)
                ))

        return results


class LogTailer:
    """Tails log files and parses entries"""

    def __init__(self, vps_name: str, app_name: str, log_files: List[str]):
        self.vps_name = vps_name
        self.app_name = app_name
        self.log_files = log_files
        self._file_positions: Dict[str, int] = {}

    def tail(self) -> List[LogEntry]:
        """Read new log entries since last tail"""
        entries = []

        for log_file in self.log_files:
            try:
                # Get current file size
                with open(log_file, 'rb') as f:
                    f.seek(0, 2)  # Seek to end
                    current_size = f.tell()

                # Get last known position
                last_pos = self._file_positions.get(log_file, 0)

                # Check for rotation (file became smaller)
                if current_size < last_pos:
                    # File was rotated/truncated - reset and read from beginning
                    last_pos = 0
                    self._file_positions[log_file] = 0

                # Read new content
                if current_size > last_pos:
                    with open(log_file, 'r') as f:
                        f.seek(last_pos)
                        new_lines = f.readlines()
                        self._file_positions[log_file] = f.tell()

                    # Parse each line
                    for line in new_lines:
                        entry = self._parse_log_line(line.strip())
                        if entry:
                            entries.append(entry)

            except FileNotFoundError:
                # Log file doesn't exist yet
                self._file_positions[log_file] = 0
            except Exception as e:
                # Log parsing error but continue
                print(f"Error tailing {log_file}: {e}")

        return entries

    def _parse_log_line(self, line: str) -> Optional[LogEntry]:
        """Parse a log line (supports both JSON and plain text)"""
        if not line:
            return None

        import json

        timestamp = datetime.utcnow()

        # Try parsing as JSON (logcore format)
        try:
            data = json.loads(line)

            # Parse timestamp if present
            parsed_timestamp = timestamp
            if 'timestamp' in data:
                try:
                    # Remove 'Z' suffix if present
                    ts_str = data['timestamp'].rstrip('Z')
                    parsed_timestamp = datetime.fromisoformat(ts_str)
                except (ValueError, AttributeError):
                    pass

            return LogEntry(
                timestamp=parsed_timestamp,
                vps_name=self.vps_name,
                app_name=self.app_name,
                level=data.get('level', 'INFO'),
                message=data.get('message', ''),
                context=data.get('context')
            )
        except (json.JSONDecodeError, ValueError):
            # Fallback: treat as plain text
            return LogEntry(
                timestamp=timestamp,
                vps_name=self.vps_name,
                app_name=self.app_name,
                level='INFO',
                message=line,
                context=None
            )
