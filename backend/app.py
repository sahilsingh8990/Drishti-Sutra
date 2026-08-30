import os
import asyncio
import cv2
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, Body, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
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
    get_hourly_volume,
    get_speed_distribution,
    get_camera_density
)
from backend.camera_manager import camera_manager
from backend.anpr_engine import anpr_engine
from backend.identity_engine import identity_engine
from backend.road_graph import road_graph
from backend.predictive_handoff_engine import predictive_engine

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_database(force=False)
    camera_manager.simulation_running = False
    yield
    camera_manager.simulation_running = False

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
    category: str
    reason: str
    severity: Optional[str] = "HIGH"

# ============================================================
# ANPR MODEL & CAMERA FEED ENDPOINTS
# ============================================================

@app.get("/api/model/status")
def get_model_status():
    model_path = Path(__file__).resolve().parent.parent / "plate_model.pt"
    return {
        "model_loaded": anpr_engine.is_loaded,
        "model_file": "plate_model.pt",
        "model_size_mb": round(model_path.stat().st_size / (1024 * 1024), 2) if model_path.exists() else 0,
        "architecture": "YOLOv11 Fine-Tuned License Plate Localization",
        "ocr_engine": "EasyOCR (English)",
        "yolo_confidence": anpr_engine.yolo_conf,
        "ocr_confidence": anpr_engine.ocr_conf,
        "indian_plates_only": anpr_engine.indian_plates_only,
        "live_camera_active": anpr_engine.live_camera_active
    }

@app.post("/api/anpr/inspect-video")
async def inspect_video(file: UploadFile = File(...)):
    import tempfile, time, numpy as np
    contents = await file.read()

    # Save to temporary file for OpenCV reading
    temp_dir = Path(__file__).resolve().parent.parent / "scratch"
    temp_dir.mkdir(exist_ok=True, parents=True)
    temp_video_path = temp_dir / f"upload_{int(time.time())}_{file.filename}"

    with open(temp_video_path, "wb") as f:
        f.write(contents)

    cap = cv2.VideoCapture(str(temp_video_path))
    if not cap.isOpened():
        raise HTTPException(status_code=400, detail="Could not open uploaded video file.")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

    frame_step = max(1, int(fps / 5))  # Sample ~5 frames per second
    frame_idx = 0
    processed_count = 0
    all_plates_detected = []
    latest_annotated_frame = None

    snapshots_dir = FRONTEND_DIR / "static" / "snapshots"
    snapshots_dir.mkdir(exist_ok=True, parents=True)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_step == 0:
                annotated_frame, detections = anpr_engine.process_frame(frame, camera_id="CAM-01")
                processed_count += 1

                if detections:
                    latest_annotated_frame = annotated_frame.copy()
                    for d in detections:
                        d["frame_index"] = frame_idx
                        d["timestamp_offset_sec"] = round(frame_idx / fps, 1)
                        all_plates_detected.append(d)

            frame_idx += 1

        # If no plate detected with annotation, save middle frame as snapshot
        if latest_annotated_frame is None and frame_idx > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_idx // 2))
            ret, frame = cap.read()
            if ret:
                latest_annotated_frame = frame

        snapshot_url = ""
        if latest_annotated_frame is not None:
            snap_path = snapshots_dir / "video_inspect_latest.jpg"
            cv2.imwrite(str(snap_path), latest_annotated_frame)
            snapshot_url = "/static/snapshots/video_inspect_latest.jpg"

    finally:
        cap.release()
        if temp_video_path.exists():
            try:
                os.remove(temp_video_path)
            except Exception:
                pass

    return {
        "success": True,
        "filename": file.filename,
        "total_video_frames": total_frames,
        "frames_processed": processed_count,
        "total_plates_detected": len(all_plates_detected),
        "plates_detected": all_plates_detected[:20],
        "snapshot_url": snapshot_url
    }

# Global Webcam Device Configurations for all 4 camera nodes
CAMERA_WEBCAM_CONFIG = {
    "CAM-01": {"active": False, "device_index": 0, "name": "Sitabuldi Central Interchange"},
    "CAM-02": {"active": False, "device_index": 1, "name": "Zero Mile Freedom Park"},
    "CAM-03": {"active": False, "device_index": 2, "name": "Nagpur Railway Station"},
    "CAM-04": {"active": False, "device_index": 3, "name": "Wardha Road Airport Flyover"}
}

class WebcamConnectInput(BaseModel):
    device_index: int = 0

@app.get("/api/cameras/webcam-status")
def get_webcam_status():
    return CAMERA_WEBCAM_CONFIG

@app.post("/api/cameras/{camera_id}/connect-webcam")
def connect_camera_webcam(camera_id: str, payload: WebcamConnectInput):
    camera_id = camera_id.upper()
    if camera_id not in CAMERA_WEBCAM_CONFIG:
        raise HTTPException(status_code=404, detail=f"Camera ID '{camera_id}' not found.")

    dev_idx = payload.device_index
    if isinstance(dev_idx, str) and dev_idx.isdigit():
        dev_idx = int(dev_idx)

    # Test opening physical webcam device
    cap = cv2.VideoCapture(dev_idx)
    if not cap.isOpened():
        raise HTTPException(
            status_code=400,
            detail=f"Webcam Device Index '{dev_idx}' could not be opened. Ensure camera is plugged into PC."
        )
    cap.release()

    CAMERA_WEBCAM_CONFIG[camera_id]["active"] = True
    CAMERA_WEBCAM_CONFIG[camera_id]["device_index"] = dev_idx
    anpr_engine.live_camera_active = True

    return {
        "status": "success",
        "message": f"Webcam Device {dev_idx} connected successfully to {camera_id}",
        "camera_id": camera_id,
        "active": True,
        "device_index": dev_idx
    }

@app.post("/api/cameras/{camera_id}/disconnect-webcam")
def disconnect_camera_webcam(camera_id: str):
    camera_id = camera_id.upper()
    if camera_id not in CAMERA_WEBCAM_CONFIG:
        raise HTTPException(status_code=404, detail=f"Camera ID '{camera_id}' not found.")

    CAMERA_WEBCAM_CONFIG[camera_id]["active"] = False
    return {
        "status": "success",
        "message": f"Webcam disconnected from {camera_id}",
        "camera_id": camera_id,
        "active": False
    }

def generate_camera_stream(camera_id: str = "CAM-01"):
    """
    Real physical webcam ANPR generator for CAM-01, CAM-02, CAM-03, CAM-04.
    Streams live OpenCV VideoCapture feed with YOLO plate detection and EasyOCR annotations.
    """
    import time, numpy as np

    camera_id = camera_id.upper()
    if camera_id not in CAMERA_WEBCAM_CONFIG:
        camera_id = "CAM-01"

    cfg = CAMERA_WEBCAM_CONFIG.get(camera_id, {"active": False, "device_index": 0, "name": "Surveillance Camera"})
    dev_idx = cfg.get("device_index", 0)

    # If webcam is marked active, stream real physical webcam video frames
    if cfg.get("active", False):
        cap = cv2.VideoCapture(dev_idx)
        if cap.isOpened():
            try:
                while cfg.get("active", False):
                    success, frame = cap.read()
                    if not success:
                        break

                    # Real-time YOLO ANPR & EasyOCR processing on physical webcam frame
                    annotated_frame, detections = anpr_engine.process_frame(frame, camera_id=camera_id)

                    # HUD overlay: Camera Node ID & Timestamp
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cv2.rectangle(annotated_frame, (0, 0), (640, 28), (10, 14, 24), -1)
                    cv2.putText(annotated_frame, f"LIVE WEBCAM [{camera_id}] (DEV {dev_idx}) - {cfg['name']}", (12, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 128), 1)
                    cv2.putText(annotated_frame, now_str, (470, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

                    _, jpeg = cv2.imencode('.jpg', annotated_frame)
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            finally:
                cap.release()
            return

    # Standby CCTV Frame when webcam is OFFLINE or disconnected (Clean, static, NO fake animations)
    frame_w, frame_h = 640, 480
    standby_frame = np.zeros((frame_h, frame_w, 3), dtype=np.uint8)
    standby_frame[:, :] = (12, 16, 26)

    # Grid line pattern for standby UI
    for y in range(0, frame_h, 40):
        cv2.line(standby_frame, (0, y), (frame_w, y), (25, 33, 50), 1)
    for x in range(0, frame_w, 40):
        cv2.line(standby_frame, (x, 0), (x, frame_h), (25, 33, 50), 1)

    # Header Bar
    cv2.rectangle(standby_frame, (0, 0), (640, 32), (18, 24, 38), -1)
    cv2.putText(standby_frame, f"NODE [{camera_id}] - {cfg['name']}", (15, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (226, 232, 240), 1)

    # Standby Badge Box
    cv2.rectangle(standby_frame, (120, 170), (520, 310), (22, 30, 46), -1)
    cv2.rectangle(standby_frame, (120, 170), (520, 310), (51, 65, 85), 2)
    cv2.putText(standby_frame, "WEBCAM DISCONNECTED / OFFLINE", (140, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (239, 68, 68), 2)
    cv2.putText(standby_frame, f"Select Device Index (0, 1, 2, 3) for {camera_id}", (155, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (148, 163, 184), 1)
    cv2.putText(standby_frame, "Click 'Connect Webcam' to start live feed", (165, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (56, 189, 248), 1)

    _, jpeg = cv2.imencode('.jpg', standby_frame)
    frame_bytes = jpeg.tobytes()

    while not cfg.get("active", False):
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(1.0)

@app.get("/api/video-feed/{camera_id}")
def video_feed_camera(camera_id: str):
    return StreamingResponse(
        generate_camera_stream(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/api/video-feed")
def video_feed(camera_id: Optional[str] = "CAM-01"):
    return StreamingResponse(
        generate_camera_stream(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

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
def list_detections(limit: int = 50, offset: int = 0, plate: Optional[str] = None, camera_id: Optional[str] = None):
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
def get_trajectory(plate_number: str, start_time: Optional[str] = None, end_time: Optional[str] = None):
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

@app.get("/api/analytics/hourly-volume")
def analytics_hourly_volume():
    return get_hourly_volume()

@app.get("/api/analytics/speed-distribution")
def analytics_speed_distribution():
    return get_speed_distribution()

@app.get("/api/analytics/camera-density")
def analytics_camera_density():
    return get_camera_density()

# Blacklist Management
@app.get("/api/blacklist")
def get_blacklist():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blacklist ORDER BY date_added DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@app.post("/api/blacklist", status_code=201)
def add_blacklist(item: BlacklistInput):
    plate = identity_engine.normalize_plate(item.plate_number)
    if not plate:
        raise HTTPException(status_code=400, detail="Registration plate number is required.")

    reason = item.reason.strip() if item.reason else ""
    if not reason:
        raise HTTPException(status_code=400, detail="Watch reason description is required.")

    category = item.category.strip().upper() if item.category else "SUSPICIOUS"
    severity = item.severity.strip().upper() if item.severity else "HIGH"

    conn = get_connection()
    cursor = conn.cursor()

    # Check for existing record
    cursor.execute("SELECT * FROM blacklist WHERE plate_number = ?", (plate,))
    existing = cursor.fetchone()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if existing:
        conn.close()
        raise HTTPException(status_code=409, detail=f"Vehicle '{plate}' already exists in active watchlist registry.")

    cursor.execute("""
        INSERT INTO blacklist (plate_number, category, reason, severity, date_added, active)
        VALUES (?, ?, ?, ?, ?, 1)
    """, (plate, category, reason, severity, now_str))
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": f"Plate {plate} registered on Priority Watchlist",
        "record": {
            "plate_number": plate,
            "category": category,
            "reason": reason,
            "severity": severity,
            "date_added": now_str,
            "active": 1
        }
    }

@app.delete("/api/blacklist/{plate_number}")
def remove_blacklist(plate_number: str):
    plate = plate_number.strip().upper()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM blacklist WHERE plate_number = ?", (plate,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Plate {plate} removed from blacklist"}

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

# ============================================================
# DRISHTI-SUTRA PREDICTIVE HANDOFF ENGINE ENDPOINTS
# ============================================================

@app.get("/api/predictive/active-tracks")
def get_active_tracks():
    """Returns active tracked vehicle entities with candidate identities and next predictions."""
    tracks = list(identity_engine.active_tracks.values())
    results = []
    for t in tracks[-25:]:
        last_cam = t["last_camera_id"]
        preds = road_graph.get_downstream_camera_predictions(last_cam)
        results.append({
            "track_id": t["track_id"],
            "resolved_plate": t["resolved_plate"],
            "raw_ocr": t["raw_ocr"],
            "identity_confidence": t["identity_confidence"],
            "candidate_identities": t["candidate_identities"],
            "vehicle_type": t["vehicle_type"],
            "last_camera_id": last_cam,
            "last_seen_timestamp": t["last_seen_timestamp"],
            "sightings_count": t["sightings_count"],
            "next_predictions": preds[:3]
        })
    return results

@app.get("/api/predictive/track/{plate_number}")
def get_predictive_track(plate_number: str):
    """
    Detailed predictive vehicle track dossier:
    - Candidate identity confidence distribution
    - Observed waypoints
    - Inferred intermediate path hypotheses
    - Ranked next cameras with ETA and factor-level explainability breakdown
    - Active watch queue status
    """
    clean_plate = identity_engine.clean_plate(plate_number)
    normalized = identity_engine.normalize_plate(clean_plate)

    # 1. Trajectory historical reconstruction
    traj_data = reconstruct_trajectory(clean_plate)
    if not traj_data["found"] and normalized != clean_plate:
        traj_data = reconstruct_trajectory(normalized)

    # Determine last sighting camera
    if traj_data["found"] and traj_data["waypoints"]:
        last_wp = traj_data["waypoints"][-1]
        last_cam_id = last_wp["camera_id"]
        vtype = last_wp["vehicle_type"]
        is_bl = traj_data["summary"]["is_blacklisted"]
        det_conf = last_wp["detection_conf"]
        ocr_conf = last_wp["ocr_conf"]
    else:
        last_cam_id = "CAM-01"
        vtype = "Sedan"
        is_bl = False
        det_conf = 0.95
        ocr_conf = 0.92

    # 2. Compute predictive handoff breakdown
    pred_res = predictive_engine.predict_next_cameras(
        plate_number=clean_plate,
        current_camera_id=last_cam_id,
        detection_conf=det_conf,
        ocr_conf=ocr_conf,
        vehicle_type=vtype,
        is_blacklisted=is_bl
    )

    # 3. Check active handoffs for this plate
    active_watches = [h for h in predictive_engine.active_handoffs.values() if identity_engine.plate_similarity(h["vehicle_plate"], clean_plate) >= 0.80]

    return {
        "found": traj_data["found"],
        "plate_number": pred_res["resolved_plate"],
        "raw_ocr": clean_plate,
        "normalized_ocr": pred_res["normalized_ocr"],
        "identity_confidence": pred_res["identity_confidence"],
        "candidate_identities": pred_res["candidate_identities"],
        "vehicle_type": vtype,
        "is_blacklisted": is_bl,
        "summary": traj_data.get("summary"),
        "observed_waypoints": traj_data.get("waypoints", []),
        "route_hypotheses": pred_res["route_hypotheses"],
        "next_camera_predictions": pred_res["predictions"],
        "active_handoffs": active_watches,
        "network_observability": road_graph.calculate_network_observability()
    }

@app.get("/api/predictive/handoffs")
def get_active_handoffs():
    """Returns all cameras currently in WATCHING FOR VEHICLE state."""
    return predictive_engine.get_active_watch_queue()

@app.get("/api/predictive/reacquisition-stats")
def get_reacquisition_stats():
    """Returns evaluation metrics: prediction accuracy, ETA errors, and recent reacquisitions."""
    return predictive_engine.get_reacquisition_statistics()

@app.get("/api/predictive/network-observability")
def get_network_observability():
    """Returns network visibility percentage, active blind spots, and camera health."""
    return road_graph.calculate_network_observability()

@app.get("/api/predictive/topology")
def get_road_topology():
    """Returns full road network graph nodes and directed links for GIS Leaflet rendering."""
    return road_graph.get_topology_geojson()

@app.post("/api/cameras/{camera_id}/status")
def set_camera_health(camera_id: str, status: str = Body(..., embed=True)):
    """
    Sets camera health status: ONLINE, OFFLINE, DEGRADED.
    Used for simulating camera failures and evaluating blind spot handling.
    """
    status = status.upper()
    if status not in ["ONLINE", "OFFLINE", "DEGRADED"]:
        raise HTTPException(status_code=400, detail="Invalid status. Must be ONLINE, OFFLINE, or DEGRADED.")

    road_graph.set_camera_status(camera_id, status)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE cameras SET status = ? WHERE id = ?", (status, camera_id))
    conn.commit()
    conn.close()

    observability = road_graph.calculate_network_observability()

    camera_manager.broadcast_sync({
        "event": "CAMERA_HEALTH_CHANGED",
        "data": {
            "camera_id": camera_id,
            "status": status,
            "observability": observability
        }
    })

    return {
        "camera_id": camera_id,
        "status": status,
        "observability": observability
    }

@app.get("/api/cameras/health")
def get_cameras_health():
    """Returns status of all cameras in the grid."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, sector, status, camera_type FROM cameras ORDER BY id ASC")
    cams = [dict(r) for r in cursor.fetchall()]
    conn.close()

    for c in cams:
        c["graph_status"] = road_graph.camera_statuses.get(c["id"], c["status"])

    return {
        "cameras": cams,
        "observability": road_graph.calculate_network_observability()
    }

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

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await camera_manager.connect_websocket(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        camera_manager.disconnect_websocket(websocket)

@app.get("/", response_class=FileResponse)
def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    return FileResponse(str(index_file))
