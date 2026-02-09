# Observ Monitoring Guide

Complete guide to fleet monitoring integration with the deployment paradigm.

## Overview

The observ monitoring system automatically collects metrics, health checks, and logs from deployed applications, storing them in a centralized PostgreSQL database and displaying them in the Fleet Hub dashboard.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│ Application │────▶│  obs-agent   │────▶│  PostgreSQL  │
│   (Flask)   │     │  (systemd)   │     │   Database   │
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │  Fleet Hub   │
                                          │  Dashboard   │
                                          └──────────────┘
```

### Components

1. **obs_agent**: Monitoring agent daemon that runs as a systemd service
   - Collects system metrics (CPU, memory, disk, network)
   - Performs HTTP health checks
   - Tails application log files
   - Writes data to PostgreSQL

2. **logcore**: Structured JSON logging library
   - Drop-in replacement for Python logging
   - Automatic context capture
   - JSON formatting for easy parsing

3. **Fleet Hub**: Web dashboard for monitoring
   - Real-time fleet overview
   - Time-series metrics visualization
   - Log search and filtering
   - Health check history

4. **PostgreSQL**: Centralized data storage
   - Three tables: vps_metrics, health_checks, app_logs
   - Optimized indexes for fast queries
   - Materialized view for fleet summary

## Setup

### 1. Database Setup

Create the PostgreSQL database and schema:

```bash
# Create database
createdb observ_metrics

# Load schema
psql observ_metrics < fleet_hub/schema.sql
```

Get your connection string:

```bash
postgresql://user:password@localhost:5432/observ_metrics
```

### 2. Application Setup with Monitoring

When setting up a new application, enable monitoring:

```bash
deploy-paradigm setup myapp https://github.com/user/myapp.git

# When prompted:
# Enable observ monitoring for this application? [y/N]: y
# PostgreSQL connection string: postgresql://user:pass@host:5432/observ_metrics
```

This will:
- Add monitoring configuration to `config.yml`
- Create a postDeploy hook to install obs-agent
- Set up the agent systemd service

### 3. Manual Configuration

If you need to add monitoring to an existing application:

**Edit `/opt/deployments/myapp/config.yml`:**

```yaml
port: 8000
manager: systemd
env: production

# Add monitoring section
monitoring:
  enabled: true
  postgres_url: ${OBSERV_DB_URL}  # or direct connection string
  collection_interval: 60
  health_checks:
    - url: http://localhost:8000/health
      interval: 30
      timeout: 5
  log_files:
    - /opt/deployments/myapp/current/logs/app.log
```

**Set environment variable:**

```bash
echo "OBSERV_DB_URL=postgresql://user:pass@host:5432/observ_metrics" >> /opt/deployments/myapp/.env.production
```

**Create postDeploy hook:**

```bash
mkdir -p /opt/deployments/myapp/hooks
cat > /opt/deployments/myapp/hooks/postDeploy <<'EOF'
#!/bin/bash
/opt/deployment-paradigm/templates/setup-monitoring.sh myapp
EOF
chmod +x /opt/deployments/myapp/hooks/postDeploy
```

**Deploy to trigger hook:**

```bash
git push production main
```

### 4. Using LogCore in Your Application

Update your application to use LogCore for structured logging:

**Before (standard logging):**

```python
import logging
logger = logging.getLogger(__name__)

logger.info("User logged in")
logger.error("Database connection failed")
```

**After (LogCore):**

```python
from logcore import get_logger
logger = get_logger(__name__)

logger.info("User logged in", extra={'context': {'user_id': 123}})
logger.error("Database connection failed", extra={'context': {'host': 'db.example.com'}})
```

LogCore automatically:
- Formats logs as JSON
- Adds timestamps and log levels
- Captures context data
- Writes to configured log files

**Update requirements.txt:**

```
# Add to your application's requirements.txt
logcore
```

### 5. Running Fleet Hub Dashboard

Start the Fleet Hub web dashboard:

```bash
# Set database URL
export OBSERV_DB_URL="postgresql://user:pass@host:5432/observ_metrics"

# Run dashboard
python -m fleet_hub

# Or with custom port
python -m fleet_hub --port 8080
```

Access the dashboard:
- Web UI: http://localhost:8080
- API docs: http://localhost:8080/docs

## Verification

### Check Agent Status

```bash
# Check if obs-agent service is running
sudo systemctl status obs-agent-myapp

# View agent logs
sudo journalctl -u obs-agent-myapp -f
```

### Query Database Directly

```bash
# Check recent metrics
psql observ_metrics -c "SELECT * FROM vps_metrics ORDER BY timestamp DESC LIMIT 5;"

# Check health checks
psql observ_metrics -c "SELECT * FROM health_checks ORDER BY timestamp DESC LIMIT 5;"

# Check logs
psql observ_metrics -c "SELECT * FROM app_logs ORDER BY timestamp DESC LIMIT 5;"

# View fleet summary
psql observ_metrics -c "SELECT * FROM fleet_summary;"
```

### Test Health Checks

```bash
# Ensure your application has a /health endpoint
curl http://localhost:8000/health

# Should return:
# {"status": "healthy"}
```

## Configuration Reference

### Monitoring Configuration (config.yml)

```yaml
monitoring:
  # Enable/disable monitoring
  enabled: true

  # PostgreSQL connection string
  # Use ${VAR} for environment variable substitution
  postgres_url: ${OBSERV_DB_URL}

  # Metrics collection interval (seconds)
  collection_interval: 60

  # HTTP health check endpoints
  health_checks:
    - url: http://localhost:8000/health
      interval: 30  # Check every 30 seconds
      timeout: 5    # 5 second timeout

    - url: http://localhost:8000/api/status
      interval: 60
      timeout: 10

  # Log files to monitor
  # Use {app} placeholder for app name
  log_files:
    - /opt/deployments/{app}/current/logs/app.log
    - /opt/deployments/{app}/current/logs/error.log
```

### systemd Service Template

The obs-agent runs as a systemd service:

```ini
[Unit]
Description=Observ Monitoring Agent for myapp
After=network.target myapp.service
Wants=myapp.service

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/deployments/myapp/current
Environment=PYTHONPATH=/opt/deployments/myapp/current
ExecStart=/opt/deployments/myapp/venv/bin/python -m obs_agent.agent \
    --config /opt/deployments/myapp/config.yml \
    --app-name myapp
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Fleet Hub API

### Endpoints

**GET /api/fleet/summary**
- Get summary of all VPS instances
- Returns: List of VPS with latest metrics and health status

**GET /api/vps/{vps_name}/metrics?hours=24**
- Get time-series metrics for a VPS
- Query params: `hours` (1-168)

**GET /api/vps/{vps_name}/health?hours=24**
- Get health check history
- Query params: `hours` (1-168)

**GET /api/logs/recent?limit=100**
- Get recent log entries
- Query params: `vps_name`, `app_name`, `level`, `limit` (1-1000)

**GET /api/logs/search?query=error&limit=100**
- Full-text search of logs
- Query params: `query`, `vps_name`, `app_name`, `level`, `hours`, `limit`

### Example API Usage

```bash
# Get fleet summary
curl http://localhost:8080/api/fleet/summary

# Get metrics for specific VPS
curl http://localhost:8080/api/vps/web-01/metrics?hours=24

# Search logs
curl "http://localhost:8080/api/logs/search?query=error&limit=50"

# Get recent logs from specific app
curl "http://localhost:8080/api/logs/recent?app_name=myapp&limit=100"
```

## Troubleshooting

### Agent Not Starting

```bash
# Check service status
sudo systemctl status obs-agent-myapp

# View detailed logs
sudo journalctl -u obs-agent-myapp -n 50

# Common issues:
# - PostgreSQL connection failed: Check OBSERV_DB_URL in .env file
# - Config file not found: Ensure config.yml exists
# - Permission denied: Check file permissions
```

### No Metrics in Database

```bash
# Verify agent is running
sudo systemctl is-active obs-agent-myapp

# Check database connection
psql $OBSERV_DB_URL -c "SELECT 1;"

# Check if metrics table exists
psql $OBSERV_DB_URL -c "\dt"

# Manually test agent
cd /opt/deployments/myapp/current
python -m obs_agent.agent --config config.yml --app-name myapp
```

### Health Checks Failing

```bash
# Test endpoint directly
curl -v http://localhost:8000/health

# Check application logs
tail -f /opt/deployments/myapp/current/logs/app.log

# Verify endpoint in config
grep -A 5 "health_checks:" /opt/deployments/myapp/config.yml
```

### Fleet Hub Connection Error

```bash
# Check OBSERV_DB_URL is set
echo $OBSERV_DB_URL

# Test database connection
psql $OBSERV_DB_URL -c "SELECT COUNT(*) FROM vps_metrics;"

# Check Fleet Hub logs
# Run in foreground to see errors
python -m fleet_hub
```

## Best Practices

### 1. Health Check Endpoints

Always implement a `/health` endpoint in your application:

```python
@app.route('/health')
def health():
    # Check critical dependencies
    db_ok = check_database()
    redis_ok = check_redis()

    if db_ok and redis_ok:
        return {'status': 'healthy'}, 200
    else:
        return {'status': 'unhealthy', 'db': db_ok, 'redis': redis_ok}, 503
```

### 2. Structured Logging

Use LogCore with context for better searchability:

```python
# Good: Structured with context
logger.info("Payment processed", extra={
    'context': {
        'order_id': order.id,
        'amount': order.total,
        'user_id': user.id
    }
})

# Bad: String formatting
logger.info(f"Payment processed for order {order.id}")
```

### 3. Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: Normal operations (user actions, requests)
- **WARNING**: Something unusual but handled
- **ERROR**: Errors that need attention

### 4. Monitoring Intervals

- **Metrics collection**: 60s (default) - adjust based on importance
- **Health checks**: 30s for critical endpoints, 60s+ for status pages
- **Log tailing**: Continuous with buffering

### 5. Database Maintenance

```sql
-- Refresh materialized view periodically (cron job)
REFRESH MATERIALIZED VIEW CONCURRENTLY fleet_summary;

-- Clean old data (keep last 30 days)
DELETE FROM vps_metrics WHERE timestamp < NOW() - INTERVAL '30 days';
DELETE FROM health_checks WHERE timestamp < NOW() - INTERVAL '30 days';
DELETE FROM app_logs WHERE timestamp < NOW() - INTERVAL '30 days';
```

## Production Deployment

### Security

1. **Database Access**: Use SSL for PostgreSQL connections
   ```
   postgres_url: postgresql://user:pass@host:5432/db?sslmode=require
   ```

2. **Fleet Hub**: Run behind reverse proxy (nginx) with authentication

3. **Secrets**: Always use environment variables for sensitive data
   ```yaml
   postgres_url: ${OBSERV_DB_URL}  # Never hardcode credentials
   ```

### Scaling

- **Multiple VPS**: Each VPS runs its own obs-agent, all write to central DB
- **Database**: Use connection pooling and indexes (already configured in schema)
- **Fleet Hub**: Can run on separate server or same as PostgreSQL
- **High Frequency**: Reduce collection_interval for high-traffic apps (30s or 15s)

### High Availability

- **Agent Restart**: systemd automatically restarts failed agents
- **Application Independence**: Agent runs as separate service, survives app crashes
- **Database Backup**: Regular backups of observ_metrics database
- **Monitoring the Monitor**: Set up alerts on agent service status

## Next Steps

1. **Deploy first application** with monitoring enabled
2. **Verify metrics** appear in database within 60 seconds
3. **Start Fleet Hub** and view dashboard
4. **Add LogCore** to your application for structured logging
5. **Configure alerts** based on metrics and logs

For more examples, see `examples/flask-app/` for a complete monitored application.
