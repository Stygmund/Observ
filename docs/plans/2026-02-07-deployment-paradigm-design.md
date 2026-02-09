# Deployment Paradigm - Design Document

**Date:** 2026-02-07
**Status:** Approved
**Goal:** Create a standardized deployment pattern for all VPS-based applications with minimal fleet monitoring

## Problem Statement

Currently deploying multiple bespoke applications to various VPSs using custom git hooks per project. This leads to:
- Inconsistent deployment processes across projects
- No standardized health checks or rollback mechanisms
- No visibility into what's deployed where
- No log aggregation across servers

**Goal:** Create ONE deployment paradigm that works for all apps (Python, Node.js, Docker) with optional fleet-wide monitoring.

## Architecture Overview

Two complementary tools:

### 1. Deployment Paradigm (Core)
Standardized deployment system triggered by `git push`:
- Installed on each VPS
- Called by git post-receive hooks
- Supports: Python, Node.js, Docker deployments
- Features: zero-downtime, health checks, automatic rollback

### 2. Fleet Monitor (Optional)
Lightweight monitoring dashboard:
- Runs on local machine
- Pulls data via rsync every 30s
- Shows fleet-wide health + log search
- No agents, just SSH + SQLite

**Integration:** Git hooks → Deployment Paradigm → logs status → Fleet Monitor displays

## Key Design Decisions

### 1. Deployment Strategy: Symlink Swap
```bash
/opt/deployments/{app}/
├── releases/
│   ├── 1707319401/  # Old release
│   └── 1707319402/  # New release
├── current -> releases/1707319402/  # Symlink
└── config.yml       # VPS-specific config
```

**Why:** Simple, fast rollback (repoint symlink), works with all process managers.

### 2. Git Hook Integration
Keep familiar `git push production main` workflow, but hook calls Deployment Paradigm for safety features.

```
Local: git push production main
  ↓
VPS: post-receive hook
  ↓
VPS: /usr/local/bin/deploy-paradigm execute
  ↓
Result: Health check + rollback + logging
```

### 3. Configuration Separation

**In repo (deploy.yml) - App identity:**
```yaml
name: my-api
type: python
healthCheck: /health
command: python -m uvicorn main:app
```

**On VPS (config.yml) - Environment config:**
```yaml
port: 8000
manager: systemd
env: production
```

**Why:** App config is in git, environment config stays on VPS. No templating needed.

### 4. Python-Only Implementation
- Python already on all VPSs (zero install overhead)
- Single-file scripts (~500 lines each)
- Minimal dependencies (click, pyyaml, requests)

### 5. Monitoring via Existing Tools + Custom Dashboard
- Netdata for system metrics (free, self-hosted)
- Custom dashboard for fleet-wide app status + log search
- No custom agents (just rsync + SSH)

## Project Structure

```
deployment-paradigm/
├── deploy_paradigm.py          # Core CLI (~400 lines)
│   ├── Commands: init, setup, execute
│   └── Deployers: Python, Node, Docker
├── fleet_monitor.py            # Monitoring (~200 lines)
│   ├── Collector (rsync via SSH)
│   ├── API (Flask)
│   └── SQLite storage
├── templates/
│   ├── deploy.yml.template
│   ├── post-receive.sh
│   └── app-config.yml.template
├── dashboard.html              # Single page app
├── install.sh                  # VPS installer
└── README.md
```

## Deployment Flow

```bash
git push production main
```

**Detailed steps:**

1. **Post-receive hook triggers**
   ```bash
   #!/bin/bash
   /usr/local/bin/deploy-paradigm execute $GIT_DIR $NEW_COMMIT
   ```

2. **Extract config from commit**
   ```bash
   git show $COMMIT:deploy.yml > /tmp/config.yml
   ```

3. **Create new release directory**
   ```bash
   RELEASE_DIR=/opt/deployments/{name}/releases/$(date +%s)
   git clone $REPO $RELEASE_DIR
   ```

4. **Type-specific build/install**
   - Python: `python -m venv venv && pip install -r requirements.txt`
   - Node: `npm ci --production`
   - Docker: `docker build -t {name}:$TIMESTAMP .`

5. **Environment setup**
   ```bash
   cp /opt/deployments/{name}/.env.production $RELEASE_DIR/.env
   ```

6. **Pre-deploy hook (optional)**
   ```bash
   ./hooks/pre-deploy.sh  # Migrations, etc.
   ```

7. **Zero-downtime swap**
   ```bash
   ln -sfn $RELEASE_DIR /opt/deployments/{name}/current
   systemctl reload {name}  # or pm2 reload
   ```

8. **Health check (3 attempts over 30s)**
   ```bash
   curl -f http://localhost:$PORT/health
   ```

9. **Rollback on failure**
   ```bash
   if [ "$HEALTHY" != "true" ]; then
     PREVIOUS=$(readlink /opt/deployments/{name}/previous)
     ln -sfn $PREVIOUS /opt/deployments/{name}/current
     systemctl reload {name}
     exit 1
   fi
   ```

10. **Cleanup old releases (keep last 3)**

## Configuration Schema

### deploy.yml (minimal, in repo)

```yaml
# Required fields
name: my-api              # Deployment name
type: python              # python|node|docker|static
healthCheck: /health      # Relative path (paradigm adds host:port)

# Optional fields
command: python -m uvicorn main:app  # Override default
hooks:
  preDeploy: ./scripts/migrate.sh    # Run before swap
  postDeploy: ./scripts/notify.sh    # Run after success
```

### VPS config (created by setup command)

```yaml
# /opt/deployments/{name}/config.yml
port: 8000
manager: systemd
env: production
```

## Fleet Monitoring

### Architecture

**On VPS (automatic):**
```bash
/opt/deployments/{app}/status.json
{
  "name": "api-server",
  "status": "running",
  "version": "abc123f",
  "deployed": "2024-02-07T15:43:22Z",
  "lastHealthCheck": "2024-02-07T16:00:00Z",
  "healthy": true
}

/var/log/deployments/{app}/
├── access.log
├── error.log
└── deploy.log
```

**On local machine:**
```bash
~/.fleet-monitor/
├── config.yml           # List of VPS servers
├── data/
│   └── fleet.db         # SQLite: aggregated logs + status
└── dashboard/
```

### Data Flow

```
Every 30s:
  fleet_monitor.py → rsync status.json + logs → SQLite
                  ↓
            Flask API serves data
                  ↓
            dashboard.html displays
```

### Dashboard Features

- Fleet overview: all servers + apps with health status
- Per-server drill-down: metrics charts (via Netdata iframe)
- Log search: full-text search across all servers
- Deployment history: what's deployed where + when

## Installation & Usage

### One-Time VPS Setup

```bash
curl -sSL https://install-url/install.sh | bash
# Installs deploy_paradigm.py to /usr/local/bin/
```

### Per-App Setup

```bash
# On VPS:
deploy-paradigm setup my-api git@github.com:you/my-api.git
# Prompts: port, manager, environment
# Creates: git repo + hook + systemd service

# Locally:
git remote add production user@vps:/var/repos/my-api.git
```

### In Project

```bash
# Add deploy.yml to repo:
deploy-paradigm init
# Edit deploy.yml with app details
git add deploy.yml
git commit -m "Add deployment config"
```

### Deploy

```bash
git push production main
# Output shows: deploy progress, health check, success/failure
```

### Fleet Monitoring

```bash
# On local machine:
pip install -r requirements.txt
python fleet_monitor.py
# Opens http://localhost:3333
```

## MVP Scope

### Week 1: Core Deployment
- `deploy_paradigm.py` with init, setup, execute commands
- Python deployer only
- Health check + rollback
- Test: Deploy Flask app to VPS

### Week 2: Multi-Type Support
- Add Node.js and Docker deployers
- Test: Deploy Express app + Docker app

### Week 3: Fleet Monitoring
- `fleet_monitor.py` with collector + API + dashboard
- Test: Monitor 2 VPSs with 3 apps

### Week 4: Polish
- Error handling + logging
- Documentation
- Cleanup old releases
- Optional: Notifications (Slack/Discord)

## Success Criteria

- ✅ Deploy Python/Node/Docker app in one command
- ✅ Zero-downtime works (old version stays up until new is healthy)
- ✅ Automatic rollback on health check failure
- ✅ Dashboard shows all apps + health status
- ✅ Log search across servers works
- ✅ Setup time: <5 min per VPS, <2 min per app

## Deferred Features (v2)

- Blue-green deployment option (vs symlink swap)
- Canary deployments (gradual rollout)
- Multi-server deployments (deploy to cluster)
- Integration with Claude Code workflow
- Deployment approvals/gates
- Advanced monitoring (metrics, alerting)
- Docker registry support (current: build on VPS)

## Technical Constraints

- Python 3.10+ required on VPS
- SSH access required from local machine
- Git installed on VPS
- Systemd or PM2 for process management
- Apps must expose HTTP health check endpoint

## Dependencies

**Core:**
- click (CLI framework)
- pyyaml (config parsing)
- requests (health checks)

**Fleet Monitor:**
- flask (web API)
- paramiko or subprocess (SSH/rsync)
- sqlite3 (stdlib, no install)

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Deploy fails mid-process | Atomic symlink swap + rollback on failure |
| Health check false positive | Retry 3x over 30s before declaring healthy |
| Disk space fills up | Auto-cleanup keeps last 3 releases only |
| Git hook conflicts | Uses standard post-receive, plays nice with others |
| Python version mismatch | Specify minimum Python 3.10 in install script |
| Fleet monitor loses connection | Agents buffer locally (logs persist), monitor catches up |

## Open Questions

- Should pre-deploy hooks block on failure? (Yes - abort deploy)
- How to handle secrets in .env files? (Manual copy to VPS, never in git)
- Support for database migrations? (Yes, via preDeploy hook)
- Notifications? (v2 - add webhook support to config)

## Alternatives Considered

### For Deployment
- **Dokku/CapRover:** Too heavy, requires Docker everywhere
- **Ansible/Fabric:** More complex, overkill for simple deploys
- **Keep custom hooks:** No standardization, hard to maintain

**Chosen:** Custom paradigm - right balance of simplicity + standardization

### For Monitoring
- **Prometheus + Grafana:** Heavy, complex setup
- **SaaS (Datadog, Better Stack):** Cost + lock-in
- **Just Netdata:** No fleet view, no log aggregation

**Chosen:** Netdata + custom dashboard - lightweight + fits needs

## Next Steps

1. Initialize git repo
2. Create implementation plan (using superpowers:writing-plans)
3. Set up git worktree (using superpowers:using-git-worktrees)
4. Implement Week 1 MVP (core deployment)
