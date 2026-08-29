import os
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.database import get_connection, init_db
from backend.seed_data import seed_database
from backend.trajectory_engine import reconstruct_trajectory
from backend.analytics_engine import (
    get_overview_kpis,
    get_traffic_density_heatmap,
    get_od_matrix,
    get_congestion_bottlenecks,
    get_hourly_volume_trends,
)
from backend.camera_manager import camera_manager

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure DB is initialized and seeded
    init_db()
    seed_database(force=False)
    # Start live city traffic background simulator
    sim_task = asyncio.create_task(camera_manager.start_background_simulation())
    yield
    # Shutdown
    camera_manager.simulation_running = False
    if sim_task:
        sim_task.cancel()

app = FastAPI(
    title="City-Wide AI Engine for Multi-Camera ANPR Trajectory Tracking & Urban Traffic Analytics",
    description="Enterprise API for multi-camera ANPR tracking, GIS trajectory reconstruction, macro urban traffic flow analytics, and security alerts.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files mount
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# ============================================================
# PYDANTIC SCHEMAS
# ============================================================

class DetectionInput(BaseModel):
    plate_number: str
    camera_id: str
    detection_conf: Optional[float] = 0.95
    ocr_conf: Optional[float] = 0.92
    vehicle_type: Optional[str] = "Sedan"
    speed_kmh: Optional[float] = 45.0
    snapshot_path: Optional[str] = ""
    raw_text: Optional[str] = ""

class BlacklistInput(BaseModel):
    plate_number: str
    category: str  # STOLEN, WANTED, SUSPICIOUS, VIOLATOR, EXPIRED_DOCS
    reason: str
    severity: Optional[str] = "HIGH"

# ============================================================
# API ROUTES
# ============================================================

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "City-Wide ANPR Trajectory & Traffic Analytics"}

@app.get("/api/cameras")
def list_cameras():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cameras ORDER BY id ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.get("/api/detections")
def list_detections(
    limit: int = 50,
    offset: int = 0,
    plate: Optional[str] = None,
    camera_id: Optional[str] = None
):
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT d.*, c.name as camera_name, c.sector
        FROM detections d
        JOIN cameras c ON d.camera_id = c.id
        WHERE 1=1
    """
    params = []
    if plate:
        query += " AND d.plate_number LIKE ?"
        params.append(f"%{plate.strip().upper()}%")
    if camera_id:
        query += " AND d.camera_id = ?"
        params.append(camera_id)

    query += " ORDER BY d.timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.post("/api/detections")
async def create_detection(item: DetectionInput):
    res = await camera_manager.record_detection(
        plate_number=item.plate_number,
        camera_id=item.camera_id,
        detection_conf=item.detection_conf,
        ocr_conf=item.ocr_conf,
        vehicle_type=item.vehicle_type,
        speed_kmh=item.speed_kmh,
        snapshot_path=item.snapshot_path,
        raw_text=item.raw_text
    )
    return res

@app.get("/api/trajectory/{plate_number}")
def get_trajectory(
    plate_number: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
):
    res = reconstruct_trajectory(plate_number, start_time, end_time)
    return res

@app.get("/api/analytics/overview")
def analytics_overview():
    return get_overview_kpis()

@app.get("/api/analytics/heatmap")
def analytics_heatmap():
    return get_traffic_density_heatmap()

@app.get("/api/analytics/od-matrix")
def analytics_od_matrix():
    return get_od_matrix()

@app.get("/api/analytics/congestion")
def analytics_congestion():
    return get_congestion_bottlenecks()

@app.get("/api/analytics/hourly-trends")
def analytics_hourly_trends():
    return get_hourly_volume_trends()

# Blacklist Management
@app.get("/api/blacklist")
def get_blacklist():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blacklist ORDER BY date_added DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.post("/api/blacklist")
def add_blacklist(item: BlacklistInput):
    plate = item.plate_number.strip().upper()
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT OR REPLACE INTO blacklist (plate_number, category, reason, severity, date_added, active)
        VALUES (?, ?, ?, ?, ?, 1)
    """, (plate, item.category.upper(), item.reason, item.severity.upper(), now_str))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Plate {plate} added to blacklist"}

@app.delete("/api/blacklist/{plate_number}")
def remove_blacklist(plate_number: str):
    plate = plate_number.strip().upper()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM blacklist WHERE plate_number = ?", (plate,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Plate {plate} removed from blacklist"}

# Security Alerts
@app.get("/api/alerts")
def get_alerts(limit: int = 50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, c.name as camera_name, c.sector
        FROM alerts a
        LEFT JOIN cameras c ON a.camera_id = c.id
        ORDER BY a.timestamp DESC LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.post("/api/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "alert_id": alert_id}

@app.post("/api/simulation/toggle")
def toggle_simulation(enabled: bool = Body(..., embed=True)):
    camera_manager.simulation_running = enabled
    if enabled:
        asyncio.create_task(camera_manager.start_background_simulation())
    return {"simulation_running": camera_manager.simulation_running}

# Exportable Vehicle Investigation Dossier
@app.get("/api/export-dossier/{plate_number}", response_class=HTMLResponse)
def export_dossier(plate_number: str):
    traj = reconstruct_trajectory(plate_number)
    if not traj["found"]:
        raise HTTPException(status_code=404, detail="Vehicle trajectory not found")

    summary = traj["summary"]
    waypoints = traj["waypoints"]
    b_info = summary.get("blacklist_info")

    wp_rows_html = ""
    for wp in waypoints:
        anomaly_tag = f"<span style='color:#ef4444;font-weight:bold;'>⚠️ {wp['anomaly_reason']}</span>" if wp["is_anomaly"] else "<span style='color:#10b981;'>Normal Transit</span>"
        wp_rows_html += f"""
        <tr>
            <td style="padding:10px; border-bottom:1px solid #334155;"><strong>Step #{wp['step']}</strong></td>
            <td style="padding:10px; border-bottom:1px solid #334155;">{wp['camera_name']} <br><small style="color:#94a3b8;">({wp['sector']})</small></td>
            <td style="padding:10px; border-bottom:1px solid #334155;">{wp['timestamp']}</td>
            <td style="padding:10px; border-bottom:1px solid #334155;">{wp['leg_distance_km']} km</td>
            <td style="padding:10px; border-bottom:1px solid #334155;">{wp['leg_speed_kmh']} km/h</td>
            <td style="padding:10px; border-bottom:1px solid #334155;">{round(wp['detection_conf']*100, 1)}% / {round(wp['ocr_conf']*100, 1)}%</td>
            <td style="padding:10px; border-bottom:1px solid #334155;">{anomaly_tag}</td>
        </tr>
        """

    blacklist_html = ""
    if b_info:
        blacklist_html = f"""
        <div style="background:#450a0a; border:1px solid #ef4444; border-radius:8px; padding:16px; margin-bottom:20px;">
            <h3 style="color:#f87171; margin:0 0 8px 0;">🚨 CRITICAL SECURITY WATCHLIST MATCH</h3>
            <p style="margin:4px 0;"><strong>Category:</strong> {b_info['category']} | <strong>Severity:</strong> {b_info['severity']}</p>
            <p style="margin:4px 0;"><strong>Reason:</strong> {b_info['reason']}</p>
            <p style="margin:4px 0; color:#cbd5e1; font-size:12px;">Added on: {b_info['date_added']}</p>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Vehicle Trajectory Dossier - {plate_number}</title>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#0f172a; color:#f8fafc; margin:0; padding:30px; }}
            .container {{ max-width: 960px; margin: 0 auto; background:#1e293b; padding:30px; border-radius:12px; border:1px solid #334155; }}
            .header {{ display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #38bdf8; padding-bottom:15px; margin-bottom:20px; }}
            .stats-grid {{ display:grid; grid-template-columns: repeat(4, 1fr); gap:15px; margin-bottom:25px; }}
            .stat-card {{ background:#0f172a; padding:15px; border-radius:8px; border:1px solid #334155; text-align:center; }}
            .stat-val {{ font-size:22px; font-weight:bold; color:#38bdf8; }}
            .stat-lbl {{ font-size:12px; color:#94a3b8; text-transform:uppercase; margin-top:5px; }}
            table {{ width:100%; border-collapse:collapse; text-align:left; font-size:13px; }}
            th {{ background:#0f172a; padding:12px; border-bottom:2px solid #475569; color:#94a3b8; text-transform:uppercase; font-size:11px; }}
            .print-btn {{ background:#0284c7; color:#fff; border:none; padding:8px 16px; border-radius:6px; cursor:pointer; font-weight:bold; }}
            @media print {{
                .print-btn {{ display:none; }}
                body {{ background:#fff; color:#000; }}
                .container {{ border:none; background:#fff; color:#000; }}
                .stat-card {{ background:#f1f5f9; border:1px solid #cbd5e1; }}
                .stat-val {{ color:#0284c7; }}
                th {{ background:#e2e8f0; color:#334155; }}
                td {{ border-bottom:1px solid #cbd5e1 !important; color:#0f172a; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1 style="margin:0; color:#38bdf8; font-size:24px;">🛡️ City ANPR Intelligence Dossier</h1>
                    <p style="margin:5px 0 0 0; color:#94a3b8; font-size:14px;">Vehicle Spatio-Temporal Trajectory & Investigation Report</p>
                </div>
                <div style="text-align:right;">
                    <button class="print-btn" onclick="window.print()">🖨️ Print / Save PDF</button>
                    <div style="font-size:11px; color:#64748b; margin-top:5px;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                </div>
            </div>

            {blacklist_html}

            <div style="background:#0f172a; border-radius:8px; padding:15px; margin-bottom:20px; border:1px solid #334155; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="color:#94a3b8; font-size:12px; text-transform:uppercase;">Registration Number:</span>
                    <div style="font-size:28px; font-weight:900; letter-spacing:2px; color:#fbbf24; font-family:monospace;">{plate_number}</div>
                </div>
                <div>
                    <span style="color:#94a3b8; font-size:12px; text-transform:uppercase;">Vehicle Classification:</span>
                    <div style="font-size:18px; font-weight:bold; color:#f8fafc;">{summary['vehicle_type']}</div>
                </div>
                <div>
                    <span style="color:#94a3b8; font-size:12px; text-transform:uppercase;">Tracking Span:</span>
                    <div style="font-size:14px; font-weight:bold; color:#f8fafc;">{summary['total_elapsed_minutes']} mins ({summary['total_sightings']} nodes)</div>
                </div>
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-val">{summary['total_distance_km']} km</div>
                    <div class="stat-lbl">Total Distance</div>
                </div>
                <div class="stat-card">
                    <div class="stat-val">{summary['avg_speed_kmh']} km/h</div>
                    <div class="stat-lbl">Average Speed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-val">{summary['total_sightings']}</div>
                    <div class="stat-lbl">Camera Nodes</div>
                </div>
                <div class="stat-card">
                    <div class="stat-val" style="color:{'#ef4444' if summary['anomaly_count'] > 0 else '#10b981'};">{summary['anomaly_count']}</div>
                    <div class="stat-lbl">Route Anomalies</div>
                </div>
            </div>

            <h3 style="margin:20px 0 10px 0; color:#38bdf8;">Chronological Waypoint Audit Trail</h3>
            <table>
                <thead>
                    <tr>
                        <th>Sequence</th>
                        <th>Camera Node & Sector</th>
                        <th>Timestamp</th>
                        <th>Distance</th>
                        <th>Speed</th>
                        <th>Conf (YOLO/OCR)</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {wp_rows_html}
                </tbody>
            </table>

            <div style="margin-top:30px; border-top:1px solid #334155; padding-top:15px; font-size:12px; color:#64748b; text-align:center;">
                City-Wide AI Engine for Multi-Camera ANPR Trajectory Tracking & Urban Traffic Analytics &bull; Autonomous Trajectory Reconstruction System
            </div>
        </div>
    </body>
    </html>
    """
    return html

# WebSocket Endpoint
@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await camera_manager.connect_websocket(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        camera_manager.disconnect_websocket(websocket)

# Serve Frontend Index
@app.get("/", response_class=FileResponse)
def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    return FileResponse(str(index_file))
