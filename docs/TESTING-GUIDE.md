# VPS Testing Guide

Complete guide for testing the deployment paradigm on a real VPS.

## Prerequisites

- Hetzner Cloud account (or DigitalOcean/Vultr)
- SSH key configured
- Local git repository ready
- Flask example app in `examples/flask-app/`

## Part 1: VPS Setup (15 minutes)

### 1.1 Create VPS

**Hetzner Cloud:**
```bash
# Via web UI:
1. Go to https://console.hetzner.cloud/
2. Create new project: "deployment-testing"
3. Add server:
   - Location: Nuremberg (or closest to you)
   - Image: Ubuntu 22.04
   - Type: CPX11 (2 vCPU, 2GB RAM) - €3.79/month
   - SSH Key: Add your public key
   - Name: deploy-test-1
4. Create & start
5. Note the IP address
```

### 1.2 Initial Server Setup

```bash
# SSH into server
ssh root@<VPS_IP>

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3 python3-pip python3-venv git curl

# Install Docker (for Docker deployer testing)
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Verify installations
python3 --version  # Should be 3.10+
docker --version
git --version

# Create deploy user (optional but recommended)
adduser deploy
usermod -aG sudo deploy
usermod -aG docker deploy
```

### 1.3 Install Deployment Paradigm

```bash
# Clone repository
cd /opt
git clone https://github.com/YOUR_USERNAME/deployment-paradigm.git
cd deployment-paradigm

# Install Python dependencies
pip3 install -r requirements.txt

# Make CLI accessible
ln -s /opt/deployment-paradigm/deploy_paradigm.py /usr/local/bin/deploy-paradigm
chmod +x /opt/deployment-paradigm/deploy_paradigm.py

# Verify installation
deploy-paradigm --help
```

## Part 2: Test Python Deployer with Simple Strategy (20 minutes)

### 2.1 Setup Flask App Deployment

```bash
# On VPS
deploy-paradigm setup flask-test https://github.com/YOUR_USERNAME/deployment-paradigm.git \
  --port 8000 \
  --manager systemd

# This creates:
# - /var/repos/flask-test.git (bare git repo)
# - /opt/deployments/flask-test/ (deployment directory)
# - systemd service (if applicable)
```

### 2.2 Configure Flask Example App

```bash
# Locally, in your deployment-paradigm repo
cd examples/flask-app

# Add deploy.yml if not exists
cat > deploy.yml <<EOF
name: flask-test
type: python
healthCheck: /health

deployment:
  strategy: simple

hooks:
  preDeploy: echo "Running pre-deploy hook"
EOF

# Commit
git add deploy.yml
git commit -m "test: add deploy config for VPS testing"

# Add VPS remote
git remote add vps root@<VPS_IP>:/var/repos/flask-test.git

# Deploy!
git push vps main
```

### 2.3 Verify Deployment

```bash
# On VPS, check deployment status
ls -la /opt/deployments/flask-test/
# Should see: releases/, current -> releases/TIMESTAMP

# Check if app is running
curl http://localhost:8000/health
# Should return: {"status": "healthy"}

# Check from your local machine
curl http://<VPS_IP>:8000/health

# If firewall blocks, open port:
ufw allow 8000/tcp
```

**✅ Checklist:**
- [ ] Git push triggered deployment
- [ ] Release directory created with timestamp
- [ ] Dependencies installed in venv
- [ ] Symlink points to current release
- [ ] Health check returns 200
- [ ] App accessible from local machine

## Part 3: Test Blue-Green Strategy (15 minutes)

### 3.1 Switch to Blue-Green

```bash
# Locally, update deploy.yml
cat > examples/flask-app/deploy.yml <<EOF
name: flask-test
type: python
healthCheck: /health

deployment:
  strategy: blue-green
  keepInactive: true

smokeTests:
  - endpoint: /
    expectedStatus: 200
  - endpoint: /health
    expectedStatus: 200
EOF

git add deploy.yml
git commit -m "test: switch to blue-green deployment"
git push vps main
```

### 3.2 Verify Blue-Green

```bash
# On VPS, check directory structure
ls -la /opt/deployments/flask-test/
# Should see: blue/, green/, current -> blue (or green)

# Check both environments
ls /opt/deployments/flask-test/blue/code
ls /opt/deployments/flask-test/green/code

# Check which is active
readlink /opt/deployments/flask-test/current
```

**✅ Checklist:**
- [ ] Blue and green directories exist
- [ ] Inactive environment was created
- [ ] Smoke tests ran successfully
- [ ] Traffic switched to new environment
- [ ] Old environment kept running (if keepInactive: true)

## Part 4: Test Rolling Strategy (15 minutes)

### 4.1 Install PM2 for Rolling Deployment

```bash
# On VPS
apt install -y nodejs npm
npm install -g pm2

# Start app with PM2 in cluster mode
pm2 delete all  # Clean slate
pm2 start /opt/deployments/flask-test/current/venv/bin/python \
  --name flask-test \
  --interpreter none \
  -- -m flask run --host 0.0.0.0 --port 8000 \
  -i 2  # 2 instances

pm2 save
pm2 startup  # Enable startup on boot
```

### 4.2 Deploy with Rolling Strategy

```bash
# Locally, update deploy.yml
cat > examples/flask-app/deploy.yml <<EOF
name: flask-test
type: python
healthCheck: /health

deployment:
  strategy: rolling
  batchDelay: 5  # Shorter for testing
EOF

git add deploy.yml
git commit -m "test: switch to rolling deployment"
git push vps main
```

### 4.3 Monitor Rolling Deployment

```bash
# On VPS, watch PM2 during deployment
pm2 logs flask-test --lines 50

# Check PM2 status
pm2 status

# Verify both instances restarted
pm2 describe flask-test
```

**✅ Checklist:**
- [ ] PM2 cluster running with 2+ instances
- [ ] Rolling restart updated instances one-by-one
- [ ] No downtime during deployment
- [ ] All instances running after deployment
- [ ] Health check passed after rolling update

## Part 5: Test Docker Deployer (20 minutes)

### 5.1 Create Simple Docker App

```bash
# Locally, create docker example
mkdir -p examples/docker-app
cd examples/docker-app

# Create simple Flask app
cat > app.py <<'EOF'
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return {'message': 'Hello from Docker!'}

@app.route('/health')
def health():
    return {'status': 'healthy'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
EOF

# Create Dockerfile
cat > Dockerfile <<'EOF'
FROM python:3.9-slim
WORKDIR /app
COPY app.py .
RUN pip install flask
EXPOSE 8000
CMD ["python", "app.py"]
EOF

# Create deploy.yml
cat > deploy.yml <<'EOF'
name: docker-test
type: docker
healthCheck: /health

deployment:
  strategy: simple

command: docker run -d --name docker-test -p 8001:8000 docker-test:latest
EOF

git add .
git commit -m "test: add Docker example app"
```

### 5.2 Setup Docker App on VPS

```bash
# On VPS
deploy-paradigm setup docker-test https://github.com/YOUR_USERNAME/deployment-paradigm.git \
  --port 8001 \
  --manager systemd

# Add remote locally
git remote add vps-docker root@<VPS_IP>:/var/repos/docker-test.git

# Deploy!
git push vps-docker main
```

### 5.3 Verify Docker Deployment

```bash
# On VPS
docker images | grep docker-test
# Should see: docker-test with timestamp tag and latest

docker ps | grep docker-test
# Should see running container

# Test endpoint
curl http://localhost:8001/health

# Check image cleanup (should keep last 3)
docker images docker-test
```

**✅ Checklist:**
- [ ] Docker image built from Dockerfile
- [ ] Image tagged with timestamp and latest
- [ ] Container running on port 8001
- [ ] Health check accessible
- [ ] Old images cleaned up (keeps last 3)

## Part 6: Test Rollback (10 minutes)

### 6.1 Simulate Failed Deployment

```bash
# Locally, break the health check
# In flask-app/app.py, change health endpoint to return 500
# OR change deploy.yml healthCheck to wrong path

git commit -am "test: break health check"
git push vps main

# Watch deployment fail and rollback
```

### 6.2 Verify Rollback

```bash
# On VPS, check logs
tail -50 /var/log/deployments/flask-test/deploy.log

# Verify current symlink points to previous release
readlink /opt/deployments/flask-test/current
# Should point to previous working release

# App should still be accessible
curl http://localhost:8000/health
```

**✅ Checklist:**
- [ ] Deployment detected failed health check
- [ ] Automatic rollback triggered
- [ ] Symlink reverted to previous release
- [ ] App still accessible on old version
- [ ] Error logged appropriately

## Part 7: Performance & Cleanup (10 minutes)

### 7.1 Test Multiple Deployments

```bash
# Make 5 quick deployments to test cleanup
for i in {1..5}; do
  echo "# Deployment $i" >> examples/flask-app/README.md
  git commit -am "test: deployment $i"
  git push vps main
  sleep 10
done

# On VPS, verify only last 3 releases kept
ls /opt/deployments/flask-test/releases/
# Should see exactly 3 directories
```

### 7.2 Check Disk Usage

```bash
# On VPS
df -h /opt/deployments/

# Check Docker image cleanup
docker images docker-test
# Should only have last 3 tagged images + latest
```

### 7.3 Cleanup Test Resources

```bash
# On VPS (when done testing)
pm2 delete all
docker stop $(docker ps -aq)
docker rm $(docker ps -aq)

# Optionally, destroy VPS via Hetzner console
# Or keep it for future testing at €3.79/month
```

**✅ Checklist:**
- [ ] Release cleanup working (keeps last 3)
- [ ] Docker image cleanup working (keeps last 3)
- [ ] Disk usage reasonable
- [ ] No orphaned processes

## Troubleshooting

### Git push hangs
```bash
# On VPS, check git hook permissions
chmod +x /var/repos/flask-test.git/hooks/post-receive
```

### Health check fails
```bash
# Check if app is running
ps aux | grep python
curl -v http://localhost:8000/health

# Check logs
journalctl -u flask-test -f  # systemd
pm2 logs flask-test           # PM2
```

### Permission denied errors
```bash
# Fix deployment directory permissions
chown -R deploy:deploy /opt/deployments/
chmod -R 755 /opt/deployments/
```

## Success Criteria

**All tasks complete:**
- [x] VPS provisioned and accessible
- [x] Deployment paradigm installed
- [x] Simple strategy works (Python)
- [x] Blue-green strategy works
- [x] Rolling strategy works (PM2)
- [x] Docker deployer works
- [x] Rollback works on failed health check
- [x] Cleanup works (releases and images)

## Next Steps

After successful testing:
1. Document any issues found in GitHub Issues
2. Update README with production deployment guide
3. Create example Ansible playbook for VPS setup
4. Add CI/CD integration guide
