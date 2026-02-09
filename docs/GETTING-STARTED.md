# Getting Started with Observ

This guide will walk you through setting up Observ for the first time, from installation to deploying your first application with monitoring.

## Prerequisites

Before you begin, ensure you have:

- **VPS or Server**: Ubuntu 20.04+ or similar Linux distribution
- **PostgreSQL**: Version 12 or higher (for monitoring)
- **Git**: Installed on both local machine and VPS
- **Python**: 3.8 or higher on VPS
- **SSH Access**: To your VPS with sudo privileges

## Step 1: Install Observ on Your VPS

### Option A: Quick Install (Recommended)

```bash
curl -sSL https://raw.githubusercontent.com/yourusername/observ/main/install.sh | bash
```

### Option B: Manual Install

```bash
# Clone repository
sudo git clone https://github.com/yourusername/observ /opt/observ
cd /opt/observ

# Install Python dependencies
pip install -r requirements.txt

# Create symlink for easy access
sudo ln -s /opt/observ/deploy_paradigm.py /usr/local/bin/deploy-paradigm

# Verify installation
deploy-paradigm --version
```

## Step 2: Setup PostgreSQL for Monitoring

### Install PostgreSQL (if not installed)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Create Monitoring Database

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE observ_metrics;
CREATE USER observ WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE observ_metrics TO observ;
\q
```

### Initialize Schema

```bash
psql -U observ -d observ_metrics < /opt/observ/fleet_hub/schema.sql
```

### Set Database URL

Add to `/etc/environment` or your shell profile:

```bash
export OBSERV_DB_URL="postgresql://observ:your-secure-password@localhost:5432/observ_metrics"
```

## Step 3: Prepare Your Application

### 1. Add Health Check Endpoint

Your application must expose a `/health` endpoint that returns 200 when healthy.

**Flask Example:**
```python
from flask import Flask
app = Flask(__name__)

@app.route('/health')
def health():
    return {'status': 'healthy'}, 200
```

**FastAPI Example:**
```python
from fastapi import FastAPI
app = FastAPI()

@app.get('/health')
def health():
    return {'status': 'healthy'}
```

### 2. Create Deployment Configuration

In your project root, create `deploy.yml`:

```yaml
name: my-api
type: python              # or docker
healthCheck: /health
command: python -m uvicorn main:app --host 0.0.0.0 --port 8000

deployment:
  strategy: blue-green    # or simple, rolling
```

### 3. Add LogCore for Structured Logging (Optional)

Install LogCore:
```bash
pip install -e /opt/observ/logcore
```

Update your application:
```python
from logcore import get_logger

logger = get_logger(__name__)

# Instead of print() or basic logging
logger.info("User logged in", extra={'context': {'user_id': 123}})
logger.error("Payment failed", extra={'context': {'amount': 99.99, 'error': 'timeout'}})
```

Commit changes:
```bash
git add deploy.yml requirements.txt
git commit -m "Add deployment configuration and LogCore"
```

## Step 4: Setup Deployment on VPS

On your VPS, run:

```bash
deploy-paradigm setup my-api git@github.com:youruser/your-app.git \
  --port 8000 \
  --manager systemd

# When prompted:
Enable observ monitoring? [y/N]: y
```

This creates:
- Git repository at `/var/repos/my-api.git`
- Deployment directory at `/opt/deployments/my-api`
- Systemd service `my-api.service`
- Monitoring agent `obs-agent-my-api.service`

## Step 5: Add Git Remote and Deploy

On your local machine:

```bash
# Add deployment remote
git remote add production user@your-vps.com:/var/repos/my-api.git

# Push to deploy
git push production main
```

Watch the deployment process:
```
Extracting config from commit...
Creating release: 1707319402
Installing dependencies...
Running health checks...
✓ Deployment successful!
```

## Step 6: Start Fleet Hub Dashboard

On your VPS (or monitoring server):

```bash
# Ensure database URL is set
export OBSERV_DB_URL="postgresql://observ:password@localhost:5432/observ_metrics"

# Start Fleet Hub
python -m fleet_hub

# Or run in background
nohup python -m fleet_hub &

# Or create systemd service (recommended)
sudo systemctl start fleet-hub
```

Access the dashboard:
```
http://your-vps-ip:8080
```

## Step 7: Explore Fleet Hub

### Fleet Overview Tab
1. See your VPS card with real-time metrics
2. Click app badges to filter logs
3. Expand card to see metrics timeline

### Applications Tab
1. Browse all running applications
2. Check activity status (green = active, gray = idle)
3. View log counts by level
4. Click apps to view their logs

### Log Stream Tab
1. Search logs across all apps
2. Filter by level, time range
3. Export logs as JSON or CSV

### Analytics Tab
1. View log volume charts
2. Monitor response time trends
3. Check health timeline
4. Review error summaries

## Next Steps

### Secure Your Dashboard

⚠️ **Important**: Fleet Hub has no built-in authentication!

Add nginx reverse proxy with basic auth:

```nginx
server {
    listen 80;
    server_name monitoring.example.com;

    auth_basic "Fleet Hub";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
    }
}
```

### Deploy More Applications

Repeat steps 3-5 for additional applications. They'll all appear in the same Fleet Hub dashboard.

### Setup Alerts (Future)

Currently, Fleet Hub shows alerts in the UI. Future versions will support:
- Email notifications
- Slack webhooks
- PagerDuty integration

### Production Checklist

Before going to production:

- [ ] Add authentication to Fleet Hub
- [ ] Setup SSL/HTTPS (Let's Encrypt)
- [ ] Configure data retention policies
- [ ] Setup database backups
- [ ] Configure firewall rules
- [ ] Test rollback procedures
- [ ] Document runbooks for team

## Troubleshooting

### Deployment fails

**Check logs:**
```bash
tail -f /var/log/deployments/my-api/post-receive.log
```

**Common issues:**
- Health check endpoint not accessible → Check app is listening on correct port
- Dependencies fail → Check `requirements.txt` syntax
- Git push rejected → Check SSH keys and repository permissions

### Monitoring agent not running

**Check status:**
```bash
systemctl status obs-agent-my-api
journalctl -u obs-agent-my-api -f
```

**Common issues:**
- Database connection failed → Verify `OBSERV_DB_URL` in `/opt/deployments/my-api/.env.production`
- Permission denied → Check file ownership: `ls -la /opt/deployments/my-api`

### Dashboard shows no data

**Verify data collection:**
```bash
# Check database has metrics
psql $OBSERV_DB_URL -c "SELECT COUNT(*) FROM vps_metrics;"

# Check obs-agent is collecting
journalctl -u obs-agent-my-api -n 50
```

## Getting Help

- **Documentation**: [docs/](../) directory
- **FAQ**: [docs/FAQ.md](FAQ.md)
- **Troubleshooting**: [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **GitHub Issues**: Report bugs and request features
- **Discussions**: Ask questions and share tips

## What's Next?

- Read the [Fleet Hub documentation](FLEET-HUB.md) for advanced features
- Learn about [deployment strategies](../README.md#deployment-strategies)
- Explore [configuration options](../README.md#configuration)
- Check out [example configurations](../examples/)

---

**Congratulations! 🎉** You've successfully set up Observ and deployed your first monitored application!
