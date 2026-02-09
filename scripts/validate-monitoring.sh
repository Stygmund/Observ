#!/bin/bash
# validate-monitoring.sh - Validate monitoring setup on VPS
# Usage: ./scripts/validate-monitoring.sh <app-name>

set -e

APP_NAME="${1:-}"
if [ -z "$APP_NAME" ]; then
    echo "Usage: $0 <app-name>"
    exit 1
fi

echo "=== Validating Monitoring Setup for $APP_NAME ==="
echo

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check 1: Config file exists
echo "Checking configuration..."
CONFIG_FILE="/opt/deployments/$APP_NAME/config.yml"
if [ -f "$CONFIG_FILE" ]; then
    check_pass "Config file exists: $CONFIG_FILE"
else
    check_fail "Config file not found: $CONFIG_FILE"
    exit 1
fi

# Check 2: Monitoring enabled in config
if grep -q "enabled: true" "$CONFIG_FILE"; then
    check_pass "Monitoring enabled in config"
else
    check_warn "Monitoring not enabled in config"
    echo "  To enable: Edit $CONFIG_FILE and set monitoring.enabled: true"
    exit 0
fi

# Check 3: PostgreSQL URL configured
POSTGRES_URL=$(grep -A 5 "^monitoring:" "$CONFIG_FILE" | grep "postgres_url:" | cut -d: -f2- | xargs)
if [ -n "$POSTGRES_URL" ]; then
    check_pass "PostgreSQL URL configured"
else
    check_fail "PostgreSQL URL not configured"
    exit 1
fi

# Check 4: systemd service exists
SERVICE_FILE="/etc/systemd/system/obs-agent-$APP_NAME.service"
if [ -f "$SERVICE_FILE" ]; then
    check_pass "systemd service file exists: $SERVICE_FILE"
else
    check_fail "systemd service file not found"
    echo "  Run a deployment to create the service"
    exit 1
fi

# Check 5: Service is enabled
if systemctl is-enabled "obs-agent-$APP_NAME" >/dev/null 2>&1; then
    check_pass "obs-agent service is enabled"
else
    check_warn "obs-agent service not enabled"
    echo "  Run: sudo systemctl enable obs-agent-$APP_NAME"
fi

# Check 6: Service is running
if systemctl is-active "obs-agent-$APP_NAME" >/dev/null 2>&1; then
    check_pass "obs-agent service is running"
else
    check_fail "obs-agent service not running"
    echo "  Check logs: sudo journalctl -u obs-agent-$APP_NAME -n 50"
    exit 1
fi

# Check 7: Environment variable set (if using env var)
if [[ "$POSTGRES_URL" == *'$'* ]]; then
    ENV_FILE="/opt/deployments/$APP_NAME/.env.production"
    if [ -f "$ENV_FILE" ] && grep -q "OBSERV_DB_URL" "$ENV_FILE"; then
        check_pass "OBSERV_DB_URL set in environment file"
    else
        check_warn "OBSERV_DB_URL may not be set in $ENV_FILE"
        echo "  Add: OBSERV_DB_URL=postgresql://user:pass@host:5432/observ_metrics"
    fi
fi

# Check 8: Recent service activity
echo
echo "Recent service logs (last 5 lines):"
sudo journalctl -u "obs-agent-$APP_NAME" -n 5 --no-pager | tail -5

# Check 9: Database connectivity (if psql available)
if command -v psql >/dev/null 2>&1; then
    echo
    echo "Checking database..."

    # Expand environment variables in URL
    if [[ "$POSTGRES_URL" == *'$'* ]]; then
        if [ -f "/opt/deployments/$APP_NAME/.env.production" ]; then
            export $(cat "/opt/deployments/$APP_NAME/.env.production" | xargs)
            POSTGRES_URL=$(echo "$POSTGRES_URL" | envsubst)
        fi
    fi

    # Test connection
    if psql "$POSTGRES_URL" -c "SELECT 1;" >/dev/null 2>&1; then
        check_pass "Database connection successful"

        # Check for recent metrics
        METRIC_COUNT=$(psql "$POSTGRES_URL" -t -c "SELECT COUNT(*) FROM vps_metrics WHERE app_name = '$APP_NAME' AND timestamp > NOW() - INTERVAL '5 minutes';" 2>/dev/null | xargs)
        if [ -n "$METRIC_COUNT" ] && [ "$METRIC_COUNT" -gt 0 ]; then
            check_pass "Recent metrics found in database ($METRIC_COUNT records)"
        else
            check_warn "No recent metrics in database (may need to wait 60s)"
        fi
    else
        check_fail "Database connection failed"
        echo "  Check connection string: $POSTGRES_URL"
    fi
else
    check_warn "psql not available, skipping database checks"
fi

echo
echo "=== Validation Complete ==="
echo
echo "To view live logs:"
echo "  sudo journalctl -u obs-agent-$APP_NAME -f"
echo
echo "To restart service:"
echo "  sudo systemctl restart obs-agent-$APP_NAME"
echo
echo "To check service status:"
echo "  sudo systemctl status obs-agent-$APP_NAME"
