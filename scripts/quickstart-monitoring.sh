#!/bin/bash
# quickstart-monitoring.sh - Quick setup for testing fleet monitoring locally
# This script sets up a local PostgreSQL database and starts the Fleet Hub dashboard

set -e

echo "=== Fleet Monitoring Quick Start ==="
echo

# Check if PostgreSQL is installed
if ! command -v psql >/dev/null 2>&1; then
    echo "❌ PostgreSQL not found. Please install PostgreSQL first:"
    echo "  macOS: brew install postgresql"
    echo "  Ubuntu: sudo apt-get install postgresql postgresql-contrib"
    exit 1
fi

# Check if PostgreSQL is running
if ! pg_isready >/dev/null 2>&1; then
    echo "❌ PostgreSQL is not running. Start it first:"
    echo "  macOS: brew services start postgresql"
    echo "  Ubuntu: sudo systemctl start postgresql"
    exit 1
fi

echo "✓ PostgreSQL is running"
echo

# Database name
DB_NAME="observ_metrics"

# Check if database exists
if psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo "⚠ Database '$DB_NAME' already exists"
    read -p "Drop and recreate? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Dropping database..."
        dropdb "$DB_NAME" 2>/dev/null || true
    else
        echo "Using existing database"
    fi
fi

# Create database if it doesn't exist
if ! psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo "Creating database '$DB_NAME'..."
    createdb "$DB_NAME"
    echo "✓ Database created"
fi

# Load schema
SCHEMA_FILE="$(dirname "$0")/../fleet_hub/schema.sql"
if [ -f "$SCHEMA_FILE" ]; then
    echo "Loading schema..."
    psql "$DB_NAME" < "$SCHEMA_FILE" >/dev/null
    echo "✓ Schema loaded"
else
    echo "❌ Schema file not found: $SCHEMA_FILE"
    exit 1
fi

# Get connection string
DB_USER=$(whoami)
OBSERV_DB_URL="postgresql://$DB_USER@localhost:5432/$DB_NAME"

echo
echo "=== Database Ready ==="
echo "Connection string: $OBSERV_DB_URL"
echo

# Add sample data for testing
echo "Adding sample data..."
psql "$OBSERV_DB_URL" <<EOF >/dev/null
-- Sample VPS metrics
INSERT INTO vps_metrics (timestamp, vps_name, app_name, cpu_percent, memory_percent, memory_mb, disk_percent, disk_gb, load_avg_1m, load_avg_5m, load_avg_15m)
VALUES
    (NOW() - INTERVAL '5 minutes', 'localhost', 'demo-app', 25.5, 45.2, 1024.5, 60.1, 45.2, 1.2, 1.5, 1.3),
    (NOW() - INTERVAL '4 minutes', 'localhost', 'demo-app', 30.2, 46.8, 1056.2, 60.2, 45.3, 1.3, 1.5, 1.3),
    (NOW() - INTERVAL '3 minutes', 'localhost', 'demo-app', 28.7, 47.5, 1072.3, 60.3, 45.4, 1.1, 1.4, 1.3),
    (NOW() - INTERVAL '2 minutes', 'localhost', 'demo-app', 32.1, 48.2, 1088.4, 60.4, 45.5, 1.4, 1.6, 1.4),
    (NOW() - INTERVAL '1 minute', 'localhost', 'demo-app', 27.9, 48.9, 1104.5, 60.5, 45.6, 1.2, 1.5, 1.3),
    (NOW(), 'localhost', 'demo-app', 29.3, 49.5, 1120.6, 60.6, 45.7, 1.3, 1.5, 1.3);

-- Sample health checks
INSERT INTO health_checks (timestamp, vps_name, app_name, url, status_code, response_time_ms, success, error_message)
VALUES
    (NOW() - INTERVAL '3 minutes', 'localhost', 'demo-app', 'http://localhost:8000/health', 200, 15.2, true, NULL),
    (NOW() - INTERVAL '2 minutes', 'localhost', 'demo-app', 'http://localhost:8000/health', 200, 12.8, true, NULL),
    (NOW() - INTERVAL '1 minute', 'localhost', 'demo-app', 'http://localhost:8000/health', 200, 14.5, true, NULL),
    (NOW(), 'localhost', 'demo-app', 'http://localhost:8000/health', 200, 13.1, true, NULL);

-- Sample logs
INSERT INTO log_entries (timestamp, vps_name, app_name, level, message, context)
VALUES
    (NOW() - INTERVAL '5 minutes', 'localhost', 'demo-app', 'INFO', 'Application started', '{"version": "1.0.0"}'),
    (NOW() - INTERVAL '4 minutes', 'localhost', 'demo-app', 'INFO', 'Database connection established', '{"host": "localhost", "port": 5432}'),
    (NOW() - INTERVAL '3 minutes', 'localhost', 'demo-app', 'WARNING', 'High memory usage detected', '{"memory_percent": 85.2}'),
    (NOW() - INTERVAL '2 minutes', 'localhost', 'demo-app', 'INFO', 'Request processed', '{"method": "GET", "path": "/api/users", "duration_ms": 45}'),
    (NOW() - INTERVAL '1 minute', 'localhost', 'demo-app', 'ERROR', 'Failed to connect to Redis', '{"host": "redis.example.com", "error": "Connection refused"}'),
    (NOW(), 'localhost', 'demo-app', 'INFO', 'Cache cleared', '{"keys_deleted": 1234}');

-- Refresh materialized view
REFRESH MATERIALIZED VIEW fleet_summary;
EOF

echo "✓ Sample data added"
echo

# Export environment variable
export OBSERV_DB_URL="$OBSERV_DB_URL"

echo "=== Starting Fleet Hub Dashboard ==="
echo
echo "Dashboard URL: http://localhost:8080"
echo "API Documentation: http://localhost:8080/docs"
echo
echo "Environment variable set:"
echo "  export OBSERV_DB_URL='$OBSERV_DB_URL'"
echo
echo "Press Ctrl+C to stop the dashboard"
echo

# Change to project directory
cd "$(dirname "$0")/.."

# Start Fleet Hub
python3 -m fleet_hub
