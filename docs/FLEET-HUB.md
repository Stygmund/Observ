# Fleet Hub Dashboard

Fleet Hub is a modern web-based monitoring dashboard for observing deployed applications across your VPS fleet. It provides real-time metrics, log aggregation, health monitoring, and analytics in a beautiful, responsive interface.

![Fleet Hub Dashboard](../assets/dashboard-preview.png)

## Features

### 📊 Fleet Overview
- **Real-time VPS Cards**: CPU, memory, disk metrics for each server
- **Application Badges**: See all apps running on each VPS with clickable badges
- **Fleet-wide KPIs**: Total servers, average CPU/memory, health status
- **Recent Alerts**: Quick view of latest errors and warnings
- **Expandable Details**: Click any VPS card to see:
  - 24-hour metrics timeline (Chart.js)
  - Recent health check history
  - Response times and status codes

### 📦 Applications View
- **Hierarchical Organization**: VPS → Applications structure
- **Activity Status**: Live indicator showing active/idle apps (5-minute threshold)
- **Log Statistics**: ERROR, WARNING, INFO, DEBUG counts per app
- **Click-to-Filter**: Click any app to jump to its logs
- **Last Log Time**: See when each app last logged

### 📝 Log Stream
- **Full-Text Search**: Search across all logs
- **Level Filtering**: Filter by DEBUG, INFO, WARNING, ERROR
- **Time Range Selector**: 1 hour to 7 days
- **Expandable Entries**: Click to see full JSON context
- **Export**: Download logs as JSON or CSV
- **VPS/App Filtering**: Quick filters from other tabs

### 📈 Analytics
- **Log Volume Chart**: Stacked bar chart by log level (24h)
- **Response Time Trends**: Multi-line chart tracking API response times
- **Health Timeline**: Success rate over time per VPS
- **Error Summary**: Top error sources and error rate percentage

## Quick Start

### Prerequisites

- PostgreSQL 12+ (for metrics storage)
- Python 3.8+ (for Fleet Hub)
- obs-agent deployed on VPS instances (automatic with deploy-paradigm)

### 1. Setup Database

```bash
# Create database
createdb observ_metrics

# Initialize schema
psql observ_metrics < fleet_hub/schema.sql

# Set connection string
export OBSERV_DB_URL="postgresql://user:pass@localhost:5432/observ_metrics"
```

### 2. Start Fleet Hub

```bash
# Install dependencies
pip install -r requirements.txt

# Run dashboard
python -m fleet_hub

# Or specify port
python -m fleet_hub --port 8080 --host 0.0.0.0
```

### 3. Access Dashboard

Open http://localhost:8080 in your browser.

**API Documentation**: http://localhost:8080/docs (FastAPI Swagger UI)

## Configuration

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `OBSERV_DB_URL` | **Yes** | PostgreSQL connection string | - |
| `FLEET_HUB_PORT` | No | Dashboard port | 8080 |
| `FLEET_HUB_HOST` | No | Bind host | 0.0.0.0 |

### Database Connection

**Format:**
```bash
postgresql://username:password@host:port/database
```

**Examples:**
```bash
# Local development
export OBSERV_DB_URL="postgresql://postgres:password@localhost:5432/observ_metrics"

# Remote PostgreSQL
export OBSERV_DB_URL="postgresql://observ:secret@db.example.com:5432/metrics"

# Unix socket
export OBSERV_DB_URL="postgresql:///observ_metrics?host=/var/run/postgresql"
```

## Architecture

### Components

```
┌─────────────────────────────────────────────────────┐
│                   Fleet Hub (8080)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │  Fleet   │  │   Apps   │  │   Logs   │         │
│  │ Overview │  │   View   │  │  Stream  │         │
│  └──────────┘  └──────────┘  └──────────┘         │
│                FastAPI + Jinja2                     │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
          ┌────────────────┐
          │   PostgreSQL   │
          │  observ_metrics│
          └────────────────┘
                   ▲
                   │
    ┌──────────────┴──────────────┐
    │                             │
┌───▼────┐                   ┌────▼───┐
│ VPS #1 │                   │ VPS #2 │
│ obs-   │                   │ obs-   │
│ agent  │                   │ agent  │
└────────┘                   └────────┘
```

### Data Flow

1. **Metrics Collection**: `obs-agent` on each VPS collects system metrics every 60s
2. **Health Checks**: Agent performs HTTP health checks on configured endpoints
3. **Log Aggregation**: Applications use LogCore → logs stored in PostgreSQL
4. **Database Storage**: All data stored in centralized PostgreSQL database
5. **Dashboard Queries**: Fleet Hub queries PostgreSQL via optimized queries
6. **Real-time Updates**: Dashboard polls API every 30 seconds

### Database Schema

**Tables:**
- `vps_metrics` - CPU, memory, disk, load averages (time-series)
- `health_checks` - HTTP health check results
- `log_entries` - Application logs with JSON context
- `fleet_summary` - Materialized view for fast fleet overview

**See:** `fleet_hub/schema.sql` for complete schema

## API Endpoints

Fleet Hub exposes a REST API for programmatic access.

### Fleet Endpoints

**GET /api/fleet/summary**
- Returns: List of all VPS instances with latest metrics
- Response: `[{vps_name, app_name, cpu_percent, memory_percent, ...}]`

**GET /api/vps/{vps_name}/metrics?hours=24**
- Returns: Time-series metrics for specific VPS
- Query params: `hours` (1-168, default: 24)

**GET /api/vps/{vps_name}/health?hours=24**
- Returns: Health check history for specific VPS
- Query params: `hours` (1-168, default: 24)

### Log Endpoints

**GET /api/logs/recent?limit=100**
- Returns: Recent log entries
- Query params:
  - `limit` (1-1000, default: 100)
  - `vps_name` (optional filter)
  - `app_name` (optional filter)
  - `level` (optional: DEBUG|INFO|WARNING|ERROR)

**GET /api/logs/search?query=error**
- Returns: Logs matching search query
- Query params:
  - `query` (required, searches message field)
  - `vps_name`, `app_name`, `level` (optional filters)
  - `hours` (1-168, default: 24)
  - `limit` (1-1000, default: 100)

### Full API Docs

Visit http://localhost:8080/docs for interactive Swagger documentation.

## Usage Guide

### Navigating the Dashboard

**Fleet Overview Tab:**
1. View fleet-wide KPIs at the top
2. Check recent alerts panel for errors/warnings
3. Click VPS cards to expand and see detailed metrics
4. Click app badges to filter logs for that app
5. Use 📋 button to view all logs for a VPS

**Applications Tab:**
1. Browse VPS sections to see all servers
2. Each app card shows activity status and log counts
3. Red border = errors present, orange = warnings
4. Click any app card to jump to filtered logs
5. Green pulsing dot = app logged in last 5 minutes

**Log Stream Tab:**
1. Search logs with the search box (press Enter)
2. Filter by log level (DEBUG/INFO/WARNING/ERROR)
3. Select time range (1h to 7 days)
4. Click log entries to expand and see JSON context
5. Export logs as JSON or CSV for analysis

**Analytics Tab:**
1. **Error Summary**: View total errors, warnings, and error rate
2. **Log Volume**: See log activity by level over 24 hours
3. **Response Time**: Track API health check performance
4. **Health Timeline**: Monitor uptime percentage per VPS

### Filtering and Navigation

**Clickable Elements:**
- **App badges** (Fleet Overview) → filters logs for VPS + app
- **📋 button** (VPS cards) → filters logs for VPS
- **Alert items** → jumps to related logs
- **VPS cards** → expands to show detailed metrics

### Keyboard Shortcuts

- **Enter** in search box → execute search
- **Escape** → collapse expanded log entry

## Integration with Deploy Paradigm

Fleet Hub is automatically integrated when you deploy applications with monitoring enabled.

### Enable During Setup

```bash
deploy-paradigm setup myapp git@github.com:user/myapp.git

# When prompted:
Enable observ monitoring? [y/N]: y
```

### Enable for Existing Deployment

Edit `/opt/deployments/{app}/config.yml`:

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

Then restart obs-agent:
```bash
systemctl restart obs-agent-{app}
```

## Production Deployment

### Recommended Setup

1. **Database**: Managed PostgreSQL (AWS RDS, DigitalOcean, etc.)
2. **Fleet Hub**: Run on dedicated monitoring server
3. **Reverse Proxy**: Nginx/Caddy with SSL
4. **Authentication**: Add auth middleware (not included)

### Example Nginx Config

```nginx
server {
    listen 80;
    server_name monitoring.example.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Security Considerations

⚠️ **Fleet Hub has NO built-in authentication!**

**Before exposing to the internet:**
1. Add authentication (basic auth, OAuth, etc.)
2. Use HTTPS with valid SSL certificate
3. Restrict database access with firewall rules
4. Use PostgreSQL connection string with strong password
5. Consider VPN or IP allowlisting

### Performance Tuning

**Database Indexes:**
```sql
-- Already in schema.sql, but verify:
CREATE INDEX idx_vps_metrics_vps_time ON vps_metrics(vps_name, timestamp DESC);
CREATE INDEX idx_health_checks_vps_time ON health_checks(vps_name, timestamp DESC);
CREATE INDEX idx_log_entries_vps_app ON log_entries(vps_name, app_name);
CREATE INDEX idx_log_entries_time ON log_entries(timestamp DESC);
```

**Data Retention:**
```sql
-- Delete old metrics (run via cron)
DELETE FROM vps_metrics WHERE timestamp < NOW() - INTERVAL '30 days';
DELETE FROM health_checks WHERE timestamp < NOW() - INTERVAL '30 days';
DELETE FROM log_entries WHERE timestamp < NOW() - INTERVAL '7 days';
```

**Connection Pooling:**
Consider using PgBouncer for high-traffic deployments.

## Troubleshooting

### Dashboard shows "Error loading fleet data"

**Check:**
1. Is PostgreSQL running?
   ```bash
   psql $OBSERV_DB_URL -c "SELECT 1"
   ```
2. Is schema initialized?
   ```bash
   psql $OBSERV_DB_URL -c "\dt"  # Should show tables
   ```
3. Are obs-agents running?
   ```bash
   systemctl status obs-agent-*
   ```

### No metrics showing up

**Verify obs-agent is collecting:**
```bash
# Check agent logs
journalctl -u obs-agent-myapp -f

# Check database
psql $OBSERV_DB_URL -c "SELECT * FROM vps_metrics ORDER BY timestamp DESC LIMIT 5"
```

### Logs not appearing

**Check:**
1. Is your app using LogCore?
2. Are log files configured in agent config?
3. Check agent logs for errors

### Charts not loading

**Browser console:** Check for JavaScript errors

**Network tab:** Verify API endpoints return data

## Customization

### Change Port

```bash
python -m fleet_hub --port 9000
```

### Custom Theme

Edit `fleet_hub/templates/dashboard.html` CSS variables:

```css
:root {
    --bg-primary: #0a0e17;
    --accent-primary: #6366f1;
    /* ... */
}
```

### Add Custom Metrics

1. Extend `obs_agent/agent.py` to collect custom metrics
2. Add columns to `vps_metrics` table
3. Update `fleet_hub/api.py` models
4. Update dashboard HTML/JS to display new metrics

## Development

### Run Locally

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run with auto-reload
uvicorn fleet_hub.api:app --reload --port 8080
```

### Code Structure

```
fleet_hub/
├── __init__.py
├── __main__.py          # CLI entry point
├── api.py               # FastAPI application and routes
├── db.py                # Database connection helper
├── queries.py           # SQL queries
├── schema.sql           # Database schema
└── templates/
    └── dashboard.html   # Single-page dashboard UI
```

### Adding Features

**New Chart:**
1. Add JavaScript function in `dashboard.html` (e.g., `loadMyChart()`)
2. Create Chart.js visualization
3. Call from `loadAnalytics()` function

**New API Endpoint:**
1. Add query function in `queries.py`
2. Add Pydantic model in `api.py`
3. Add endpoint in `api.py`
4. Update dashboard to consume endpoint

## FAQ

**Q: Can I monitor non-Python applications?**
A: Yes! obs-agent monitors system metrics regardless of language. For logs, you can configure any log file path.

**Q: Does this work with Docker containers?**
A: Yes, obs-agent monitors the host system. For container-specific metrics, extend the agent.

**Q: Can I use a different database?**
A: PostgreSQL is required. The queries use PostgreSQL-specific features (ILIKE, JSON operators).

**Q: How do I add authentication?**
A: Use a reverse proxy (Nginx) with basic auth, or add middleware to `api.py` using FastAPI's security features.

**Q: Can multiple Fleet Hub instances share one database?**
A: Yes! Multiple read-only Fleet Hub instances can query the same database.

**Q: What's the performance impact of monitoring?**
A: Minimal. Metrics collected every 60s, health checks every 30s. CPU overhead: <1%.

## Support

- **Documentation**: `/docs` directory
- **Issues**: GitHub Issues
- **Examples**: `/examples` directory

## Related Documentation

- [Deployment Guide](../README.md) - Main deployment system docs
- [Test Monitoring Guide](../TEST-MONITORING-GUIDE.md) - Local testing setup
- [Port Conventions](../PORT-CONVENTIONS.md) - Port usage standards
- [LogCore Documentation](../logcore/README.md) - Structured logging library

## License

Apache 2.0 - See [LICENSE](../LICENSE) for details
