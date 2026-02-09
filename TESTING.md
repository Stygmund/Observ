# Manual Testing Checklist

## Prerequisites
- [ ] VPS with Python 3.10+
- [ ] SSH access to VPS
- [ ] Test Flask app repository

## Test Setup
- [ ] Run install.sh on VPS
- [ ] Verify `/usr/local/bin/deploy-paradigm` exists
- [ ] Run `deploy-paradigm --help`

## Test Init
- [ ] Create new project directory
- [ ] Run `deploy-paradigm init`
- [ ] Verify `deploy.yml` created
- [ ] Edit deploy.yml with app details

## Test Setup
- [ ] Run `deploy-paradigm setup test-app git@github.com:you/test.git`
- [ ] Verify bare repo created in `/var/repos/`
- [ ] Verify deployment dir created in `/opt/deployments/`
- [ ] Verify systemd service created

## Test Deployment
- [ ] Add git remote: `git remote add production user@vps:/var/repos/test-app.git`
- [ ] Push: `git push production main`
- [ ] Verify deployment output shows progress
- [ ] Verify release created in `/opt/deployments/test-app/releases/`
- [ ] Verify symlink points to new release
- [ ] Verify health check passed

## Test Rollback
- [ ] Deploy broken code (health check fails)
- [ ] Verify automatic rollback
- [ ] Verify previous release is running

## Cleanup
- [ ] Remove test app
- [ ] Remove deployment directories
