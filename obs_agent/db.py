"""
PostgreSQL writer for monitoring data.
"""

import json
from typing import List
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import execute_batch
from psycopg2.pool import SimpleConnectionPool

from obs_agent.collectors import MetricData, HealthCheckData, LogEntry


class PostgreSQLWriter:
    """Writes monitoring data to PostgreSQL with connection pooling"""

    def __init__(self, database_url: str, min_connections: int = 1, max_connections: int = 5):
        self.pool = SimpleConnectionPool(
            min_connections,
            max_connections,
            database_url
        )

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        conn = self.pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self.pool.putconn(conn)

    def write_metrics(self, metrics: List[MetricData]) -> None:
        """Write system metrics to vps_metrics table"""
        if not metrics:
            return

        sql = """
            INSERT INTO vps_metrics (
                timestamp, vps_name, app_name, cpu_percent, memory_percent,
                memory_mb, disk_percent, disk_gb, load_avg_1m, load_avg_5m, load_avg_15m
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """

        values = [
            (
                m.timestamp, m.vps_name, m.app_name, m.cpu_percent, m.memory_percent,
                m.memory_mb, m.disk_percent, m.disk_gb, m.load_avg_1m, m.load_avg_5m, m.load_avg_15m
            )
            for m in metrics
        ]

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_batch(cur, sql, values)

    def write_health_checks(self, checks: List[HealthCheckData]) -> None:
        """Write health check results to health_checks table"""
        if not checks:
            return

        sql = """
            INSERT INTO health_checks (
                timestamp, vps_name, app_name, url, status_code,
                response_time_ms, success, error_message
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            )
        """

        values = [
            (
                c.timestamp, c.vps_name, c.app_name, c.url, c.status_code,
                c.response_time_ms, c.success, c.error_message
            )
            for c in checks
        ]

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_batch(cur, sql, values)

    def write_logs(self, logs: List[LogEntry]) -> None:
        """Write log entries to log_entries table"""
        if not logs:
            return

        sql = """
            INSERT INTO log_entries (
                timestamp, vps_name, app_name, level, message, context
            ) VALUES (
                %s, %s, %s, %s, %s, %s
            )
        """

        values = [
            (
                log.timestamp, log.vps_name, log.app_name, log.level,
                log.message, json.dumps(log.context) if log.context else None
            )
            for log in logs
        ]

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_batch(cur, sql, values)

    def close(self):
        """Close all connections in the pool"""
        self.pool.closeall()
