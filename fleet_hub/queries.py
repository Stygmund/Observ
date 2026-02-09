"""
SQL queries for Fleet Hub dashboard
"""
from datetime import datetime
from typing import List, Optional


def get_fleet_summary(conn) -> List[dict]:
    """
    Get summary of all VPS instances using the materialized view

    Returns: List of VPS summaries with latest metrics and health status
    """
    query = """
        SELECT
            vps_name,
            app_name,
            last_seen,
            cpu_percent,
            memory_percent,
            disk_percent,
            health_status
        FROM fleet_summary
        ORDER BY last_seen DESC
    """

    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()


def get_vps_metrics(conn, vps_name: str, since: datetime) -> List[dict]:
    """
    Get time-series metrics for a specific VPS

    Args:
        conn: Database connection
        vps_name: VPS hostname
        since: Start timestamp for metrics

    Returns: List of metric data points
    """
    query = """
        SELECT
            timestamp,
            cpu_percent,
            memory_percent,
            memory_mb,
            disk_percent,
            disk_gb,
            load_avg_1m,
            load_avg_5m,
            load_avg_15m
        FROM vps_metrics
        WHERE vps_name = %s
          AND timestamp >= %s
        ORDER BY timestamp ASC
    """

    with conn.cursor() as cur:
        cur.execute(query, (vps_name, since))
        return cur.fetchall()


def get_vps_health_checks(conn, vps_name: str, since: datetime) -> List[dict]:
    """
    Get health check history for a specific VPS

    Args:
        conn: Database connection
        vps_name: VPS hostname
        since: Start timestamp for health checks

    Returns: List of health check results
    """
    query = """
        SELECT
            timestamp,
            url,
            status_code,
            response_time_ms,
            success,
            error_message
        FROM health_checks
        WHERE vps_name = %s
          AND timestamp >= %s
        ORDER BY timestamp DESC
    """

    with conn.cursor() as cur:
        cur.execute(query, (vps_name, since))
        return cur.fetchall()


def search_logs(
    conn,
    query: str,
    vps_name: Optional[str] = None,
    app_name: Optional[str] = None,
    level: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = 100
) -> List[dict]:
    """
    Full-text search of application logs

    Args:
        conn: Database connection
        query: Search query string
        vps_name: Optional VPS filter
        app_name: Optional app filter
        level: Optional log level filter
        since: Optional start timestamp
        limit: Max results

    Returns: List of matching log entries
    """
    sql = """
        SELECT
            timestamp,
            vps_name,
            app_name,
            level,
            message,
            context
        FROM log_entries
        WHERE message ILIKE %s
    """

    params = [f'%{query}%']

    if vps_name:
        sql += " AND vps_name = %s"
        params.append(vps_name)

    if app_name:
        sql += " AND app_name = %s"
        params.append(app_name)

    if level:
        sql += " AND level = %s"
        params.append(level)

    if since:
        sql += " AND timestamp >= %s"
        params.append(since)

    sql += " ORDER BY timestamp DESC LIMIT %s"
    params.append(limit)

    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_recent_logs(
    conn,
    vps_name: Optional[str] = None,
    app_name: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = 100
) -> List[dict]:
    """
    Get recent log entries with optional filters

    Args:
        conn: Database connection
        vps_name: Optional VPS filter
        app_name: Optional app filter
        level: Optional log level filter
        limit: Max results

    Returns: List of recent log entries
    """
    sql = """
        SELECT
            timestamp,
            vps_name,
            app_name,
            level,
            message,
            context
        FROM log_entries
        WHERE 1=1
    """

    params = []

    if vps_name:
        sql += " AND vps_name = %s"
        params.append(vps_name)

    if app_name:
        sql += " AND app_name = %s"
        params.append(app_name)

    if level:
        sql += " AND level = %s"
        params.append(level)

    sql += " ORDER BY timestamp DESC LIMIT %s"
    params.append(limit)

    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()
