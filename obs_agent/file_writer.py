"""
JSONL file writer for monitoring data.

Writes metrics, health checks, and logs to daily-rotated JSONL files
instead of PostgreSQL. Designed for rsync-based collection to a central server.
"""

import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List

from obs_agent.collectors import MetricData, HealthCheckData, LogEntry


class FileWriter:
    """Writes monitoring data to daily-rotated JSONL files."""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, prefix: str) -> Path:
        """Get today's JSONL file path."""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        return self.output_dir / f"{prefix}-{date_str}.jsonl"

    def _append(self, path: Path, records: list) -> None:
        """Append JSON records to a file."""
        with open(path, "a") as f:
            for record in records:
                f.write(json.dumps(record, default=str) + "\n")

    def write_metrics(self, metrics: List[MetricData]) -> None:
        if not metrics:
            return
        self._append(
            self._get_path("metrics"),
            [asdict(m) for m in metrics]
        )

    def write_health_checks(self, checks: List[HealthCheckData]) -> None:
        if not checks:
            return
        self._append(
            self._get_path("health"),
            [asdict(c) for c in checks]
        )

    def write_logs(self, logs: List[LogEntry]) -> None:
        if not logs:
            return
        self._append(
            self._get_path("logs"),
            [asdict(l) for l in logs]
        )

    def close(self):
        """No-op — files are opened/closed per write."""
        pass
