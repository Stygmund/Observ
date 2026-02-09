# Port Conventions

This document describes the standard port assignments used in the Observ project.

## Port Assignments

| Service | Default Port | Configurable? | Description |
|---------|--------------|---------------|-------------|
| **Fleet Hub Dashboard** | `8080` | Yes | Web UI for monitoring deployed applications |
| **Deployed Applications** | `8000` | Yes | Your applications being monitored |
| **PostgreSQL** | `5432` | Yes | Database for metrics and logs |

## Configuration Files

### Fleet Hub (Monitoring Dashboard)

**Start command:**
```bash
python -m fleet_hub --port 8080
```

**Where configured:**
- `fleet_hub/__main__.py` - Default port 8080
- Can be overridden with `--port` flag

**URL references:**
- Dashboard: `http://localhost:8080`
- API docs: `http://localhost:8080/docs`

### Deployed Applications

**Where configured:**
- `templates/obs-agent.yml` - Template config (port: 8000)
- `test-monitoring-config.yml` - Test config (port: 8000)
- Per-deployment: `/opt/deployments/{app}/config.yml`

**Health check URLs:**
- Applications define their own health endpoints
- Example: `http://localhost:8000/health`
- These are NOT links to Fleet Hub

## Important Notes

1. **Don't confuse the ports:**
   - `8080` = Fleet Hub (where you VIEW monitoring data)
   - `8000` = Your app (what IS BEING monitored)

2. **Health check URLs in dashboard:**
   - These show which endpoints the monitoring agent is checking
   - They point to YOUR application's port (8000)
   - They are NOT clickable links (intentionally disabled)

3. **Database connection:**
   - Set via `OBSERV_DB_URL` environment variable
   - Format: `postgresql://user:pass@host:5432/dbname`

## Changing Ports

### Change Fleet Hub port:
```bash
python -m fleet_hub --port 9000
```

### Change application port:
Edit your `config.yml`:
```yaml
port: 3000  # Your custom port

monitoring:
  health_checks:
    - url: http://localhost:3000/health  # Update URL to match
```

## Testing Configuration

For local testing (`test-monitoring-config.yml`):
- Application runs on port 8000
- Fleet Hub runs on port 8080
- Health checks point to port 8000 (the test app)
