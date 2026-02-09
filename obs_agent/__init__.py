"""
obs_agent: Lightweight VPS monitoring daemon

Collects system metrics, health checks, and logs, writing them to PostgreSQL
for fleet-wide monitoring via fleet_hub dashboard.
"""

from obs_agent.agent import MonitoringAgent
from obs_agent.collectors import SystemMetrics, HealthChecker, LogTailer

__all__ = ['MonitoringAgent', 'SystemMetrics', 'HealthChecker', 'LogTailer']
__version__ = '1.0.0'
