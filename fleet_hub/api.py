"""
Fleet Hub Dashboard - FastAPI web interface for monitoring deployed applications
"""
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

from fleet_hub.db import get_db_connection
from fleet_hub.queries import (
    get_fleet_summary,
    get_vps_metrics,
    get_vps_health_checks,
    search_logs,
    get_recent_logs
)


app = FastAPI(title="Fleet Hub", description="Observ Fleet Monitoring Dashboard")

# Setup templates
templates_dir = Path(__file__).parent / 'templates'
templates = Jinja2Templates(directory=str(templates_dir))


# Models
class VPSSummary(BaseModel):
    vps_name: str
    app_name: str
    last_seen: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    health_status: str


class MetricPoint(BaseModel):
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_percent: float
    disk_gb: float
    load_avg_1m: float
    load_avg_5m: float
    load_avg_15m: float


class HealthCheck(BaseModel):
    timestamp: datetime
    url: str
    status_code: Optional[int]
    response_time_ms: Optional[float]
    success: bool
    error_message: Optional[str]


class LogEntry(BaseModel):
    timestamp: datetime
    vps_name: str
    app_name: str
    level: str
    message: str
    context: Optional[dict]


# Endpoints
@app.get('/api/fleet/summary', response_model=List[VPSSummary])
async def fleet_summary():
    """Get summary of all VPS instances in the fleet"""
    try:
        conn = get_db_connection()
        results = get_fleet_summary(conn)
        conn.close()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get('/api/vps/{vps_name}/metrics', response_model=List[MetricPoint])
async def vps_metrics(
    vps_name: str,
    hours: int = Query(default=24, ge=1, le=168, description="Hours of metrics to retrieve")
):
    """Get time-series metrics for a specific VPS"""
    try:
        conn = get_db_connection()
        since = datetime.utcnow() - timedelta(hours=hours)
        results = get_vps_metrics(conn, vps_name, since)
        conn.close()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get('/api/vps/{vps_name}/health', response_model=List[HealthCheck])
async def vps_health(
    vps_name: str,
    hours: int = Query(default=24, ge=1, le=168, description="Hours of health checks to retrieve")
):
    """Get health check history for a specific VPS"""
    try:
        conn = get_db_connection()
        since = datetime.utcnow() - timedelta(hours=hours)
        results = get_vps_health_checks(conn, vps_name, since)
        conn.close()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get('/api/logs/search', response_model=List[LogEntry])
async def logs_search(
    query: str = Query(..., min_length=1, description="Search query"),
    vps_name: Optional[str] = Query(None, description="Filter by VPS name"),
    app_name: Optional[str] = Query(None, description="Filter by app name"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    hours: int = Query(default=24, ge=1, le=168, description="Hours of logs to search"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max results")
):
    """Search logs with full-text search"""
    try:
        conn = get_db_connection()
        since = datetime.utcnow() - timedelta(hours=hours)
        results = search_logs(conn, query, vps_name, app_name, level, since, limit)
        conn.close()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get('/api/logs/recent', response_model=List[LogEntry])
async def logs_recent(
    vps_name: Optional[str] = Query(None, description="Filter by VPS name"),
    app_name: Optional[str] = Query(None, description="Filter by app name"),
    level: Optional[str] = Query(None, description="Filter by log level"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max results")
):
    """Get recent log entries"""
    try:
        conn = get_db_connection()
        results = get_recent_logs(conn, vps_name, app_name, level, limit)
        conn.close()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get('/', response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard HTML"""
    template_path = templates_dir / 'dashboard.html'
    if not template_path.exists():
        return HTMLResponse(content="""
        <html>
            <head><title>Fleet Hub</title></head>
            <body>
                <h1>Fleet Hub Dashboard</h1>
                <p>Dashboard template not found. API endpoints are available at /docs</p>
            </body>
        </html>
        """)

    with open(template_path) as f:
        return HTMLResponse(content=f.read())


@app.get('/health')
async def health():
    """Health check endpoint"""
    return {'status': 'healthy'}


def run_server(host: str = '0.0.0.0', port: int = 8080):
    """Run the Fleet Hub server"""
    uvicorn.run(app, host=host, port=port)


if __name__ == '__main__':
    run_server()
