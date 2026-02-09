#!/usr/bin/env python3
"""
Demo script showing obs_agent and logcore usage.

This example demonstrates:
1. How to use logcore for structured JSON logging
2. How the obs_agent collectors work
3. What data gets written to PostgreSQL
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
from logcore import get_logger
from obs_agent.collectors import SystemMetrics, HealthChecker

# Setup structured logging with logcore
logger = get_logger(__name__)

def demo_structured_logging():
    """Demo structured JSON logging"""
    print("\n=== LogCore Structured Logging Demo ===")

    logger.info("Application started")
    logger.info("User login", extra={'context': {'user_id': 123, 'ip': '192.168.1.1'}})
    logger.warning("High memory usage", extra={'context': {'memory_percent': 85.5}})

    try:
        raise ValueError("Something went wrong")
    except ValueError as e:
        logger.error("Error processing request", exc_info=True, extra={'context': {'request_id': 'req-456'}})

    print("\nNote: Logs above are JSON formatted and can be parsed by obs_agent")


def demo_system_metrics():
    """Demo system metrics collection"""
    print("\n=== System Metrics Collection Demo ===")

    collector = SystemMetrics(vps_name='demo-server', app_name='demo-app')
    metrics = collector.collect()

    print(f"Timestamp:     {metrics.timestamp}")
    print(f"CPU:           {metrics.cpu_percent:.1f}%")
    print(f"Memory:        {metrics.memory_percent:.1f}% ({metrics.memory_mb:.0f} MB)")
    print(f"Disk:          {metrics.disk_percent:.1f}% ({metrics.disk_gb:.1f} GB)")
    print(f"Load Average:  {metrics.load_avg_1m:.2f}, {metrics.load_avg_5m:.2f}, {metrics.load_avg_15m:.2f}")
    print("\nThese metrics would be written to PostgreSQL vps_metrics table")


def demo_health_checks():
    """Demo HTTP health checks"""
    print("\n=== Health Check Demo ===")

    health_checks = [
        {'url': 'https://httpbin.org/status/200', 'timeout': 5},
        {'url': 'https://httpbin.org/delay/10', 'timeout': 2},  # Will timeout
    ]

    checker = HealthChecker(
        vps_name='demo-server',
        app_name='demo-app',
        health_checks=health_checks
    )

    results = checker.check()

    for result in results:
        status = "✓" if result.success else "✗"
        print(f"{status} {result.url}")
        if result.success:
            print(f"   Status: {result.status_code}, Response time: {result.response_time_ms:.0f}ms")
        else:
            print(f"   Error: {result.error_message}")

    print("\nThese results would be written to PostgreSQL health_checks table")


if __name__ == '__main__':
    print("=" * 60)
    print("Observ Monitoring System Demo")
    print("=" * 60)

    demo_structured_logging()
    demo_system_metrics()
    demo_health_checks()

    print("\n" + "=" * 60)
    print("To run the full monitoring agent:")
    print("  python -m obs_agent.agent --config /path/to/config.yml --app-name my-app")
    print("\nTo set up the database:")
    print("  createdb observ_metrics")
    print("  psql observ_metrics < fleet_hub/schema.sql")
    print("=" * 60)
