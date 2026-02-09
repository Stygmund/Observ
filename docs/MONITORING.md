# Fleet Monitoring System

Observ's fleet monitoring system provides production-grade observability for all deployed VPS instances.

## Architecture

```
[VPS 1: obs_agent] ──┐
[VPS 2: obs_agent] ──┼─→ [PostgreSQL] ←── [fleet_hub dashboard]
[VPS 3: obs_agent] ──┘
```

## Components

### obs_agent (VPS-side daemon)

Lightweight monitoring agent running on each VPS:
- Collects system metrics (CPU, memory, disk, load)
- Executes HTTP health checks
- Tails application logs
- Writes to PostgreSQL every 60s
- Resource usage: <5% CPU, <50MB RAM

### fleet_hub (Central dashboard)

FastAPI-based web dashboard:
- Real-time fleet overview
- Historical metrics charts
- Log search with full-text search
- Health status alerts

### logcore (Logging library)

Structured JSON logging for applications:
- Consistent log format across all apps
- JSON with timestamp, level, logger, message, context
- Automatic parsing by obs_agent

## Quick Start

### 1. Database Setup (One-time)

```bash
# Create database
createdb observ_metrics

# Initialize schema
psql observ_metrics < fleet_hub/schema.sql

# Set connection string
export OBSERV_DB_URL="postgresql://user:pass@localhost:5432/observ_metrics"
```

### 2. Enable Monitoring for an App

Add to `/opt/deployments/{app-name}/config.yml`:

```yaml
monitoring:
  enabled: true
  postgres_url: ${OBSERV_DB_URL}
  collection_interval: 60
  health_checks:
    - url: http://localhost:8000/health
      interval: 30
      timeout: 5
  log_files:
    - /opt/deployments/{app}/current/logs/app.log
```

Add to `/opt/deployments/{app-name}/.env.production`:

```bash
OBSERV_DB_URL=postgresql://user:pass@db.host:5432/observ_metrics
```

### 3. Install and Start Agent

```bash
# Copy systemd service template
sudo cp templates/obs-agent.service /etc/systemd/system/obs-agent@.service

# Enable and start for your app
sudo systemctl enable obs-agent@my-app
sudo systemctl start obs-agent@my-app

# Check status
sudo systemctl status obs-agent@my-app
```

### 4. Use LogCore in Your Application

```python
from logcore import get_logger

logger = get_logger(__name__, log_file='/opt/deployments/my-app/current/logs/app.log')

# Structured logging
logger.info("User action", extra={'context': {'user_id': 123}})

# Exception logging
try:
    process_payment()
except Exception as e:
    logger.error("Payment failed", exc_info=True, extra={'context': {'order_id': 456}})
```

Output:
```json
{"timestamp": "2026-02-08T20:30:00Z", "level": "INFO", "logger": "my_app", "message": "User action", "context": {"user_id": 123}}
```

## Configuration Reference

### monitoring.enabled

Enable/disable monitoring for this application.

- Type: `boolean`
- Default: `false`

### monitoring.postgres_url

PostgreSQL connection string. Supports environment variable expansion.

- Type: `string`
- Required: `yes`
- Example: `postgresql://user:pass@db.host:5432/observ_metrics`
- Example: `${OBSERV_DB_URL}` (reads from environment)

### monitoring.collection_interval

How often to collect metrics (seconds).

- Type: `integer`
- Default: `60`
- Minimum: `10`

### monitoring.health_checks

List of HTTP endpoints to check.

- Type: `array`
- Each check has:
  - `url` (string, required): HTTP(S) endpoint to check
  - `interval` (integer): Check frequency in seconds (default: same as collection_interval)
  - `timeout` (integer): Request timeout in seconds (default: 5)

Example:
```yaml
health_checks:
  - url: http://localhost:8000/health
    interval: 30
    timeout: 5
  - url: http://localhost:8000/api/status
    interval: 60
    timeout: 10
```

### monitoring.log_files

List of log files to monitor. Use `{app}` placeholder for app name.

- Type: `array`
- Default: `[]`

Example:
```yaml
log_files:
  - /opt/deployments/{app}/current/logs/app.log
  - /var/log/{app}/error.log
```

## Database Schema

### vps_metrics

System metrics collected every collection_interval.

- `id`, `timestamp`, `vps_name`, `app_name`
- `cpu_percent`, `memory_percent`, `memory_mb`
- `disk_percent`, `disk_gb`
- `load_avg_1m`, `load_avg_5m`, `load_avg_15m`

### health_checks

HTTP health check results.

- `id`, `timestamp`, `vps_name`, `app_name`
- `url`, `status_code`, `response_time_ms`
- `success`, `error_message`

### log_entries

Structured logs from applications.

- `id`, `timestamp`, `vps_name`, `app_name`
- `level`, `message`, `context` (JSONB)
- Full-text search on `message` via GIN index

## Data Retention

Recommended retention policies:

```sql
-- Keep metrics for 90 days
DELETE FROM vps_metrics WHERE timestamp < NOW() - INTERVAL '90 days';

-- Keep health checks for 90 days
DELETE FROM health_checks WHERE timestamp < NOW() - INTERVAL '90 days';

-- Keep logs for 30 days
DELETE FROM log_entries WHERE timestamp < NOW() - INTERVAL '30 days';
```

Run via cron:
```bash
# Daily at 3 AM
0 3 * * * psql observ_metrics -c "DELETE FROM log_entries WHERE timestamp < NOW() - INTERVAL '30 days';"
```

## Troubleshooting

### Agent not starting

Check systemd status:
```bash
sudo systemctl status obs-agent@my-app
sudo journalctl -u obs-agent@my-app -n 50
```

Common issues:
- PostgreSQL connection failed: Check `OBSERV_DB_URL` in `.env.production`
- Permission denied: Ensure `www-data` user has access to log files
- Config not found: Verify `/opt/deployments/{app}/config.yml` exists

### No metrics in database

Check agent logs:
```bash
sudo journalctl -u obs-agent@my-app -f
```

Verify database connection:
```bash
psql $OBSERV_DB_URL -c "SELECT COUNT(*) FROM vps_metrics WHERE app_name='my-app';"
```

### Logs not being collected

Check log file permissions:
```bash
ls -la /opt/deployments/my-app/current/logs/
```

Ensure log file exists and is readable by `www-data`:
```bash
sudo chown www-data:www-data /opt/deployments/my-app/current/logs/app.log
sudo chmod 644 /opt/deployments/my-app/current/logs/app.log
```

## Performance

Expected resource usage per agent:

- CPU: <5% (spikes during collection)
- Memory: <50MB
- Disk I/O: Minimal (60s collection interval)
- Network: ~1KB/min to PostgreSQL

Database growth (per app):

- Metrics: ~1MB/day (60s interval)
- Health checks: ~500KB/day (30s interval)
- Logs: Variable (depends on application)

## Security

The systemd service includes security hardening:

- `PrivateTmp=yes`: Isolated /tmp
- `NoNewPrivileges=yes`: No privilege escalation
- `ProtectSystem=strict`: Read-only system files
- `ProtectHome=yes`: No access to home directories
- `MemoryLimit=100M`: Resource limit
- `CPUQuota=10%`: CPU limit

## Next Steps

1. **Phase 2**: Implement fleet_hub dashboard (FastAPI + Chart.js)
2. **Phase 3**: Add deployment hooks for automatic agent setup
3. **Phase 4**: Alerting (email/Slack on health check failures)
4. **Phase 5**: Metrics aggregation and anomaly detection

## Examples

See `examples/monitoring-demo.py` for a runnable demo of:
- Structured logging with logcore
- System metrics collection
- HTTP health checks

Run with:
```bash
python3 examples/monitoring-demo.py
```
