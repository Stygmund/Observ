#!/bin/bash
# setup-monitoring.sh - Auto-configure obs_agent monitoring
# Called as postDeploy hook to install monitoring agent as systemd service

set -e

APP_NAME="${1:-}"
if [ -z "$APP_NAME" ]; then
    echo "Error: APP_NAME required"
    exit 1
fi

DEPLOYMENT_DIR="/opt/deployments/$APP_NAME"
CONFIG_FILE="$DEPLOYMENT_DIR/config.yml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if monitoring is enabled in config
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Config file not found: $CONFIG_FILE"
    exit 0
fi

# Extract monitoring.enabled from YAML (simple grep approach)
MONITORING_ENABLED=$(grep -A 1 "^monitoring:" "$CONFIG_FILE" | grep "enabled:" | awk '{print $2}' | tr -d ' ')

if [ "$MONITORING_ENABLED" != "true" ]; then
    echo "Monitoring not enabled for $APP_NAME (monitoring.enabled: $MONITORING_ENABLED)"
    exit 0
fi

echo "Setting up obs-agent monitoring for $APP_NAME..."

# Validate required config
POSTGRES_URL=$(grep -A 5 "^monitoring:" "$CONFIG_FILE" | grep "postgres_url:" | cut -d: -f2- | xargs)
if [ -z "$POSTGRES_URL" ] || [ "$POSTGRES_URL" = "\${OBSERV_DB_URL}" ]; then
    echo "Error: monitoring.postgres_url not configured in $CONFIG_FILE"
    echo "Please set a valid PostgreSQL connection string or ensure \$OBSERV_DB_URL is set in .env file"
    exit 1
fi

# Create systemd service
SERVICE_NAME="obs-agent-$APP_NAME"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

echo "Creating systemd service: $SERVICE_NAME"

# Use template if it exists, otherwise inline service definition
if [ -f "$SCRIPT_DIR/obs-agent.service.template" ]; then
    sed -e "s/{app_name}/$APP_NAME/g" \
        "$SCRIPT_DIR/obs-agent.service.template" | sudo tee "$SERVICE_FILE" > /dev/null
else
    # Inline service template
    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Observ Monitoring Agent for $APP_NAME
After=network.target $APP_NAME.service
Wants=$APP_NAME.service

[Service]
Type=simple
User=deploy
WorkingDirectory=$DEPLOYMENT_DIR/current
Environment=PYTHONPATH=$DEPLOYMENT_DIR/current
ExecStart=$DEPLOYMENT_DIR/venv/bin/python -m obs_agent.agent --config $DEPLOYMENT_DIR/config.yml --app-name $APP_NAME
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
fi

# Reload systemd and enable service
echo "Enabling and starting $SERVICE_NAME..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

# Wait a moment and check status
sleep 2
if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "✓ $SERVICE_NAME is running"
    sudo systemctl status "$SERVICE_NAME" --no-pager -l | head -10
else
    echo "✗ $SERVICE_NAME failed to start"
    sudo journalctl -u "$SERVICE_NAME" -n 20 --no-pager
    exit 1
fi

echo "✓ Monitoring setup complete for $APP_NAME"
