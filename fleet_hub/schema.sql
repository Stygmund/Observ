-- Fleet Hub PostgreSQL Schema
-- Create with: psql observ_metrics < fleet_hub/schema.sql

-- System metrics table
CREATE TABLE IF NOT EXISTS vps_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    vps_name VARCHAR(255) NOT NULL,
    app_name VARCHAR(255) NOT NULL,
    cpu_percent REAL NOT NULL,
    memory_percent REAL NOT NULL,
    memory_mb REAL NOT NULL,
    disk_percent REAL NOT NULL,
    disk_gb REAL NOT NULL,
    load_avg_1m REAL NOT NULL,
    load_avg_5m REAL NOT NULL,
    load_avg_15m REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for efficient queries by VPS, app, and time
CREATE INDEX IF NOT EXISTS idx_vps_metrics_lookup
ON vps_metrics (vps_name, app_name, timestamp DESC);

-- Index for time-based queries
CREATE INDEX IF NOT EXISTS idx_vps_metrics_timestamp
ON vps_metrics (timestamp DESC);

-- Health checks table
CREATE TABLE IF NOT EXISTS health_checks (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    vps_name VARCHAR(255) NOT NULL,
    app_name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    status_code INTEGER,
    response_time_ms REAL,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for health check queries
CREATE INDEX IF NOT EXISTS idx_health_checks_lookup
ON health_checks (vps_name, app_name, timestamp DESC);

-- Index for finding failures
CREATE INDEX IF NOT EXISTS idx_health_checks_success
ON health_checks (success, timestamp DESC);

-- Log entries table
CREATE TABLE IF NOT EXISTS log_entries (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    vps_name VARCHAR(255) NOT NULL,
    app_name VARCHAR(255) NOT NULL,
    level VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    context JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for log searches by VPS and app
CREATE INDEX IF NOT EXISTS idx_log_entries_lookup
ON log_entries (vps_name, app_name, timestamp DESC);

-- Index for log level filtering
CREATE INDEX IF NOT EXISTS idx_log_entries_level
ON log_entries (level, timestamp DESC);

-- Full-text search index on message (GIN index)
CREATE INDEX IF NOT EXISTS idx_log_entries_message_fts
ON log_entries USING GIN (to_tsvector('english', message));

-- JSONB index for context queries
CREATE INDEX IF NOT EXISTS idx_log_entries_context
ON log_entries USING GIN (context);

-- Partitioning setup (optional, for high-volume deployments)
-- Uncomment to enable monthly partitioning:

-- CREATE TABLE vps_metrics_template (LIKE vps_metrics INCLUDING ALL);
-- ALTER TABLE vps_metrics_template ADD CONSTRAINT vps_metrics_template_timestamp_check
--     CHECK (timestamp >= DATE_TRUNC('month', CURRENT_DATE));

-- Data retention policy (optional)
-- Run periodically to clean old data:

-- DELETE FROM vps_metrics WHERE timestamp < NOW() - INTERVAL '90 days';
-- DELETE FROM health_checks WHERE timestamp < NOW() - INTERVAL '90 days';
-- DELETE FROM log_entries WHERE timestamp < NOW() - INTERVAL '30 days';

-- Materialized view for dashboard fleet summary
CREATE MATERIALIZED VIEW IF NOT EXISTS fleet_summary AS
WITH latest_metrics AS (
    SELECT DISTINCT ON (vps_name, app_name)
        vps_name,
        app_name,
        timestamp as last_seen,
        cpu_percent,
        memory_percent,
        disk_percent
    FROM vps_metrics
    ORDER BY vps_name, app_name, timestamp DESC
),
recent_health AS (
    SELECT DISTINCT ON (vps_name, app_name)
        vps_name,
        app_name,
        success,
        timestamp as health_timestamp
    FROM health_checks
    WHERE timestamp > NOW() - INTERVAL '5 minutes'
    ORDER BY vps_name, app_name, timestamp DESC
)
SELECT
    m.vps_name,
    m.app_name,
    m.last_seen,
    m.cpu_percent,
    m.memory_percent,
    m.disk_percent,
    CASE
        WHEN h.success IS NULL THEN 'unknown'
        WHEN h.success = true THEN 'healthy'
        ELSE 'unhealthy'
    END as health_status
FROM latest_metrics m
LEFT JOIN recent_health h ON m.vps_name = h.vps_name AND m.app_name = h.app_name;

CREATE UNIQUE INDEX IF NOT EXISTS idx_fleet_summary_unique
ON fleet_summary (vps_name, app_name);

-- Refresh materialized view periodically (run via cron or pg_cron):
-- REFRESH MATERIALIZED VIEW CONCURRENTLY vps_summary;

-- Grant permissions for dashboard user (optional)
-- CREATE USER dashboard WITH PASSWORD 'changeme';
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO dashboard;
-- GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO dashboard;
