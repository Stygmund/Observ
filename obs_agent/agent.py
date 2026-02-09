#!/usr/bin/env python3
"""
Monitoring agent daemon - main loop for collecting and writing metrics.
"""

import os
import sys
import time
import signal
import socket
from pathlib import Path
from typing import Optional

import click
import yaml

from obs_agent.collectors import SystemMetrics, HealthChecker, LogTailer
from obs_agent.db import PostgreSQLWriter
from obs_agent.file_writer import FileWriter


class MonitoringAgent:
    """Main monitoring agent daemon"""

    def __init__(
        self,
        vps_name: str,
        app_name: str,
        writer,  # PostgreSQLWriter or FileWriter
        collection_interval: int = 60,
        health_checks: Optional[list] = None,
        log_files: Optional[list] = None
    ):
        self.vps_name = vps_name
        self.app_name = app_name
        self.collection_interval = collection_interval
        self.running = False

        # Initialize collectors
        self.metrics_collector = SystemMetrics(vps_name, app_name)
        self.health_checker = HealthChecker(vps_name, app_name, health_checks or [])
        self.log_tailer = LogTailer(vps_name, app_name, log_files or [])

        # Use provided writer (postgres or file)
        self.db_writer = writer

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully"""
        click.echo(f"\nReceived signal {signum}, shutting down...")
        self.running = False

    def run(self):
        """Main daemon loop"""
        self.running = True
        click.echo(f"Starting monitoring agent for {self.app_name} on {self.vps_name}")
        click.echo(f"Collection interval: {self.collection_interval}s")

        try:
            while self.running:
                try:
                    self._collect_and_write()
                    time.sleep(self.collection_interval)
                except Exception as e:
                    click.echo(f"Error in collection cycle: {e}", err=True)
                    # Continue despite errors
                    time.sleep(self.collection_interval)
        finally:
            self._cleanup()

    def _collect_and_write(self):
        """Single collection cycle"""
        # Collect system metrics
        metrics = self.metrics_collector.collect()
        self.db_writer.write_metrics([metrics])

        # Run health checks
        health_results = self.health_checker.check()
        if health_results:
            self.db_writer.write_health_checks(health_results)

        # Tail log files
        log_entries = self.log_tailer.tail()
        if log_entries:
            self.db_writer.write_logs(log_entries)

        # Log summary
        click.echo(
            f"[{metrics.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
            f"CPU: {metrics.cpu_percent:.1f}% | "
            f"Mem: {metrics.memory_percent:.1f}% | "
            f"Checks: {len(health_results)} | "
            f"Logs: {len(log_entries)}"
        )

    def _cleanup(self):
        """Cleanup resources"""
        click.echo("Cleaning up...")
        self.db_writer.close()
        click.echo("Agent stopped")


@click.command()
@click.option('--config', type=click.Path(exists=True), required=True, help='Path to config.yml')
@click.option('--app-name', required=True, help='Application name')
@click.option('--vps-name', default=None, help='VPS name (default: hostname)')
def main(config: str, app_name: str, vps_name: Optional[str]):
    """Run the monitoring agent daemon"""

    # Load configuration
    config_path = Path(config)
    with config_path.open() as f:
        config_data = yaml.safe_load(f)

    monitoring_config = config_data.get('monitoring', {})

    if not monitoring_config.get('enabled', False):
        click.echo("Monitoring is not enabled in config.yml", err=True)
        sys.exit(1)

    # Get VPS name (default to hostname)
    if not vps_name:
        vps_name = socket.gethostname()

    # Select output writer based on config
    output_mode = monitoring_config.get('output', 'postgres')

    if output_mode == 'file':
        output_dir = monitoring_config.get('output_dir')
        if not output_dir:
            click.echo("output_dir not configured for file output mode", err=True)
            sys.exit(1)
        output_dir = os.path.expandvars(output_dir)
        writer = FileWriter(output_dir)
    else:
        postgres_url = monitoring_config.get('postgres_url')
        if not postgres_url:
            click.echo("postgres_url not configured in monitoring section", err=True)
            sys.exit(1)
        postgres_url = os.path.expandvars(postgres_url)
        writer = PostgreSQLWriter(postgres_url)

    # Collection interval
    collection_interval = monitoring_config.get('collection_interval', 60)

    # Health checks configuration
    health_checks = monitoring_config.get('health_checks', [])

    # Log files configuration
    log_files = monitoring_config.get('log_files', [])

    # Expand variables in log file paths
    log_files = [
        path.replace('{app}', app_name)
        for path in log_files
    ]

    # Create and run agent
    agent = MonitoringAgent(
        vps_name=vps_name,
        app_name=app_name,
        writer=writer,
        collection_interval=collection_interval,
        health_checks=health_checks,
        log_files=log_files
    )

    agent.run()


if __name__ == '__main__':
    main()
