#!/bin/bash
# Fleet Hub Startup Script

export OBSERV_DB_URL="postgresql://localhost/observ_metrics"

echo "Starting Fleet Hub..."
echo "Database: $OBSERV_DB_URL"
echo ""

python -m fleet_hub --port 8080
