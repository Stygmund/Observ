# Observ 🚀

> A standardized deployment system for VPS applications with zero-downtime deploys, health checks, automatic rollback, and integrated fleet monitoring.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-12+-blue.svg)](https://www.postgresql.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

Observ combines powerful deployment automation with comprehensive fleet monitoring in a single, integrated system. Deploy applications with `git push`, monitor them in real-time with Fleet Hub, and rollback instantly if issues arise.

## 📋 Table of Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Fleet Hub Dashboard](#fleet-hub-dashboard)
- [Deployment Strategies](#deployment-strategies)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Features

### Deployment
- **Multiple deployment strategies** - Choose between simple, blue-green, or rolling deployments
- **Zero-downtime deployments** - Symlink-based swapping keeps old version running until new is healthy
- **Health checks** - Validate deployments before switching traffic
- **Smoke tests** - Run automated tests after deployment to verify functionality
- **Automatic rollback** - Failed health checks trigger instant rollback
- **Multi-type support** - Python, Node.js, Docker (Week 1: Python ✅ Docker ✅)
- **Git-based workflow** - Deploy with `git push production main`

### Fleet Monitoring (NEW! ✨)
- **Auto-installed monitoring agent** - obs_agent automatically deploys with your application
- **System metrics collection** - CPU, memory, disk, load averages every 60s
- **Health check monitoring** - Track endpoint availability and response times
- **Log aggregation** - Centralized structured logging with LogCore
- **Fleet Hub dashboard** - Beautiful real-time web interface with:
  - 📊 Fleet Overview with expandable VPS cards and KPIs
  - 📦 Applications view (hierarchical VPS → Apps)
  - 📝 Log stream with search, filtering, and export
  - 📈 Analytics with charts and error summaries
- **PostgreSQL backend** - Centralized metrics storage with optimized queries
- **Responsive design** - Works on desktop, tablet, and mobile

## 📸 Screenshots

### Fleet Hub Dashboard

**Fleet Overview**
![Fleet Overview](docs/assets/fleet-overview.png)
*Real-time VPS metrics, KPIs, and recent alerts*

**Applications View**
![Applications](docs/assets/applications-view.png)
*Hierarchical view of all apps across your fleet*

**Log Stream**
![Logs](docs/assets/log-stream.png)
*Searchable, filterable log viewer with export*

**Analytics**
![Analytics](docs/assets/analytics.png)
*Charts for log volume, response times, and health*

> **Note:** Screenshots are placeholders. Add actual screenshots to `docs/assets/` directory.

## Installation

### On VPS

```bash
curl -sSL https://raw.githubusercontent.com/stygmund/observ/main/install.sh | bash
```

Or install manually:

```bash
git clone https://github.com/stygmund/observ /opt/observ
cd /opt/observ
pip install -r requirements.txt
sudo ln -s /opt/deployment-paradigm/deploy_paradigm.py /usr/local/bin/deploy-paradigm
```

## Quick Start

### 1. Setup VPS for your app

On your VPS:

```bash
deploy-paradigm setup my-api git@github.com:youruser/my-api.git --port 8000 --manager systemd
```

This creates:
- Bare git repository at `/var/repos/my-api.git`
- Deployment directory at `/opt/deployments/my-api`
- Systemd service for your app

### 2. Configure your project

In your project repository:

```bash
deploy-paradigm init
```

Edit `deploy.yml`:

```yaml
name: my-api
type: python
healthCheck: /health
command: python -m uvicorn main:app
```

Commit and push:

```bash
git add deploy.yml
git commit -m "Add deployment config"
```

### 3. Add git remote

On your local machine:

```bash
git remote add production user@your-vps.com:/var/repos/my-api.git
```

### 4. Deploy

```bash
git push production main
```

Watch the deployment process:
- Extracts config from commit
- Creates timestamped release
- Installs dependencies in virtualenv
- Updates symlink
- Runs health check
- Rolls back if health check fails

## Configuration

### deploy.yml (in your project repo)

```yaml
# Required
name: my-api              # Application name
type: python              # python|node|docker|static
healthCheck: /health      # Health check endpoint

# Optional deployment strategy
deployment:
  strategy: blue-green    # simple or blue-green (default: simple)
  keepInactive: true      # For blue-green: keep old environment for instant rollback

# Optional smoke tests (run after deployment)
smokeTests:
  - endpoint: /api/status
    expectedStatus: 200
  - endpoint: /api/health/deep
    method: GET
  - script: ./scripts/smoke-test.sh

# Optional
command: python -m uvicorn main:app  # Custom start command

hooks:
  preDeploy: ./scripts/migrate.sh    # Run before deployment
  postDeploy: ./scripts/notify.sh    # Run after success
```

### VPS config (on server)

Located at `/opt/deployments/{app-name}/config.yml`:

```yaml
port: 8000
manager: systemd  # or pm2
env: production

# Optional: Enable monitoring
monitoring:
  enabled: true
  postgres_url: ${OBSERV_DB_URL}  # Set in .env file
  collection_interval: 60
  health_checks:
    - url: http://localhost:8000/health
      interval: 30
      timeout: 5
  log_files:
    - /opt/deployments/{app}/current/logs/app.log
```

## Directory Structure

On VPS:

```
/opt/deployments/{app-name}/
├── releases/
│   ├── 1707319401/          # Old release
│   └── 1707319402/          # New release
├── current -> releases/1707319402/  # Symlink
├── previous -> releases/1707319401/ # For rollback
├── config.yml               # VPS config
└── .env.production          # Environment variables

/var/repos/{app-name}.git/   # Bare git repository
└── hooks/
    └── post-receive         # Deployment trigger
```

## Deployment Strategies

### Simple Strategy (Default)

The simple strategy uses symlink swapping for zero-downtime deployments:

1. Clone code to timestamped release directory
2. Install dependencies
3. Run pre-deploy hooks (migrations)
4. Swap `current` symlink to new release
5. Reload service
6. Health check new release
7. Rollback if health check fails

**When to use:**
- Small to medium applications
- Single-instance deployments
- When you don't need instant rollback

**Configuration:**
```yaml
deployment:
  strategy: simple
```

### Blue-Green Strategy (Recommended)

The blue-green strategy maintains two separate environments for zero-risk deployments:

1. Deploy to inactive environment (blue or green)
2. Install dependencies in inactive environment
3. Run pre-deploy hooks
4. Start inactive service on dedicated port
5. Health check inactive environment (multiple checks)
6. Run smoke tests on inactive environment
7. Switch traffic to inactive (becomes active)
8. Optionally keep old environment for instant rollback

**When to use:**
- Production applications requiring maximum reliability
- Applications with complex health requirements
- When instant rollback is critical
- Multi-instance or load-balanced deployments

**Configuration:**
```yaml
deployment:
  strategy: blue-green
  keepInactive: true  # Keep old environment running for instant rollback
```

**Benefits:**
- Test deployment in production environment before switching traffic
- Instant rollback (just switch symlink back)
- Run comprehensive smoke tests before going live
- Zero downtime even if deployment fails

**Note:** Blue-green deployments require your application to run on configurable ports and a reverse proxy (nginx/traefik) to route traffic.

### Rolling Strategy

The rolling strategy performs gradual instance-by-instance updates:

1. Clone code to timestamped release directory
2. Install dependencies
3. Run pre-deploy hooks (migrations)
4. Update `current` symlink to new release
5. Rolling restart (PM2 reloads instances one-by-one, systemd does graceful reload)
6. Wait for stabilization
7. Health check after all instances updated
8. Rollback if health check fails

**When to use:**
- Multi-instance applications (PM2 cluster mode)
- Applications with multiple systemd services
- When you want gradual rollout without separate environments
- Load-balanced applications with health checks

**Configuration:**
```yaml
deployment:
  strategy: rolling
  batchDelay: 10  # Seconds to wait for stabilization (default: 10)
```

**Benefits:**
- Gradual rollout reduces blast radius
- No duplicate infrastructure needed (unlike blue-green)
- Works with PM2 cluster mode out of the box
- Graceful restarts minimize connection drops

**Process Manager Support:**
- **PM2:** Uses `pm2 reload` which does zero-downtime rolling restart
- **Systemd:** Uses `reload-or-restart` for graceful service reload

**Note:** For true rolling deployments, use PM2 cluster mode or multiple systemd service instances.

## Health Checks

Your application must expose a health check endpoint that returns HTTP 200 when healthy.

Example (Flask):

```python
@app.route('/health')
def health():
    return {'status': 'healthy'}, 200
```

Example (FastAPI):

```python
@app.get('/health')
def health():
    return {'status': 'healthy'}
```

**Simple Strategy:**
1. Wait 10s after restarting the app
2. Make 3 health check attempts (5s apart)
3. Rollback if any attempt fails

**Blue-Green Strategy:**
1. Wait 10s after starting inactive environment
2. Make 5 health check attempts (2s apart)
3. Run smoke tests
4. Only switch if all checks pass

## Smoke Tests

Smoke tests allow you to validate your deployment beyond basic health checks. They run only in blue-green deployments before switching traffic.

**Endpoint tests:**
```yaml
smokeTests:
  - endpoint: /api/users
    method: GET
    expectedStatus: 200
  - endpoint: /api/status
    expectedStatus: 200
    expectedBody: "ok"
```

**Script tests:**
```yaml
smokeTests:
  - script: ./scripts/integration-test.sh
```

Scripts should exit with code 0 for success, non-zero for failure.

## Rollback

Automatic rollback happens when:
- Health check fails
- Pre-deploy hook fails

Manual rollback:

```bash
# On VPS
cd /opt/deployments/my-api
ln -sfn previous current
systemctl reload my-api
```

## Troubleshooting

**Deployment fails with "deploy.yml not found"**
- Ensure `deploy.yml` is committed to your repository
- Check you're pushing the correct branch

**Health check fails**
- Verify your app exposes the health endpoint
- Check logs: `/var/log/deployments/{app-name}/`
- Ensure the port matches config

**Dependencies fail to install**
- Check `requirements.txt` syntax
- Verify Python version compatibility
- Check VPS has internet access

## Monitoring

The observ system includes integrated fleet monitoring for all deployed applications.

### Quick Start

**1. Setup database:**

```bash
createdb observ_metrics
psql observ_metrics < fleet_hub/schema.sql
export OBSERV_DB_URL="postgresql://user:pass@localhost:5432/observ_metrics"
```

**2. Enable monitoring during setup:**

```bash
deploy-paradigm setup myapp git@github.com:youruser/myapp.git

# When prompted:
# Enable observ monitoring? [y/N]: y
```

**3. Add LogCore to your application:**

```python
from logcore import get_logger
logger = get_logger(__name__)

logger.info("Request processed", extra={'context': {'user_id': 123}})
```

**4. Start Fleet Hub dashboard:**

```bash
export OBSERV_DB_URL="postgresql://user:pass@localhost:5432/observ_metrics"
python -m fleet_hub
```

Access dashboard at http://localhost:8080

### What Gets Monitored

- **System Metrics**: CPU, memory, disk, load averages (every 60s)
- **Health Checks**: HTTP endpoint availability and response times
- **Application Logs**: Structured JSON logs with full-text search
- **Fleet Overview**: Real-time status of all deployed applications

### Fleet Hub Dashboard

The Fleet Hub dashboard provides a comprehensive view of your entire fleet:

**Fleet Overview Tab:**
- Fleet-wide KPIs (total servers, avg CPU/memory, health status)
- Recent alerts panel with clickable navigation
- VPS cards showing real-time metrics
- Clickable app badges for each server
- Expandable cards with 24h metrics timeline and health checks

**Applications Tab:**
- Hierarchical view: VPS → Applications
- Activity indicators (active/idle based on last log)
- Log statistics by level (ERROR, WARNING, INFO, DEBUG)
- Click-to-filter navigation

**Log Stream Tab:**
- Full-text search across all logs
- Filter by level, VPS, app, and time range
- Expandable entries showing full JSON context
- Export to JSON/CSV

**Analytics Tab:**
- Log volume charts by level (24h)
- Response time trends
- Health timeline (uptime percentage)
- Error summary with top sources

### Architecture

Each deployed application automatically gets:
- `obs-agent` systemd service for metrics collection
- LogCore structured logging library
- Centralized PostgreSQL storage
- Fleet Hub web dashboard access

**📖 Complete Fleet Hub documentation: [docs/FLEET-HUB.md](docs/FLEET-HUB.md)**

## Development

Run tests:

```bash
pytest tests/ -v
```

## 🗺️ Roadmap

### Completed ✅
- [x] Core deployment system (Python, Docker)
- [x] Blue-green and rolling strategies
- [x] Fleet monitoring with obs-agent
- [x] Fleet Hub dashboard with comprehensive UI
- [x] Log aggregation with LogCore
- [x] Real-time metrics and health checks

### In Progress 🚧
- [ ] Authentication for Fleet Hub
- [ ] Data retention policies
- [ ] Node.js deployment support

### Planned 📋
- [ ] Alerting and notifications (email, Slack, webhooks)
- [ ] Real-time updates via WebSocket
- [ ] Custom dashboards
- [ ] Multi-tenancy support
- [ ] Container-specific metrics

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

## 📚 Documentation

- **[Fleet Hub Guide](docs/FLEET-HUB.md)** - Complete dashboard documentation
- **[Port Conventions](PORT-CONVENTIONS.md)** - Port usage standards
- **[Test Monitoring Guide](TEST-MONITORING-GUIDE.md)** - Local testing setup
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute
- **[Changelog](CHANGELOG.md)** - Version history

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details on:
- Setting up development environment
- Code style guidelines
- Submitting pull requests
- Reporting bugs and suggesting features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/) and [Chart.js](https://www.chartjs.org/)
- Inspired by modern deployment platforms like Heroku and Vercel
- Thanks to all contributors who help improve Observ

## 📞 Support

- **Documentation**: Check the [docs/](docs/) directory
- **Issues**: [GitHub Issues](https://github.com/stygmund/observ/issues)
- **Discussions**: [GitHub Discussions](https://github.com/stygmund/observ/discussions)

---

Made with ❤️ by the Observ community
