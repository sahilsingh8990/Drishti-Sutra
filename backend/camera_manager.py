import asyncio
import random
from datetime import datetime
from typing import List, Dict, Any
from backend.database import get_connection
from backend.trajectory_engine import haversine

class CameraManager:
    def __init__(self):
        self.active_websockets = []
        self.simulation_running = False
        self.sim_task = None

    async def connect_websocket(self, websocket):
        await websocket.accept()
        self.active_websockets.append(websocket)

    def disconnect_websocket(self, websocket):
        if websocket in self.active_websockets:
            self.active_websockets.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        disconnected = []
        for ws in self.active_websockets:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect_websocket(ws)

    def broadcast_sync(self, message: Dict[str, Any]):
        """Safely broadcast messages across synchronous calls and background threads."""
        try:
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                pass

            if loop and loop.is_running():
                loop.create_task(self.broadcast(message))
            else:
                for ws in list(self.active_websockets):
                    try:
                        asyncio.run(ws.send_json(message))
                    except Exception:
                        pass
        except Exception as e:
            pass

    def record_detection_sync(
        self,
        plate_number: str,
        camera_id: str = "CAM-01",
        detection_conf: float = 0.95,
        ocr_conf: float = 0.92,
        vehicle_type: str = "Live Camera Feed",
        speed_kmh: float = 45.0,
        snapshot_path: str = "",
        raw_text: str = ""
    ) -> Dict[str, Any]:
        """
        Synchronously and immediately records detection into SQLite DB,
        checks for blacklist & anomalies, and broadcasts to dashboard UI.
        """
        raw_text = raw_text or plate_number
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Resolve vehicle identity early via Confidence-Aware Identity Engine
        from backend.identity_engine import identity_engine
        resolved_entity = identity_engine.resolve_or_update_identity(
            raw_ocr=plate_number,
            camera_id=camera_id,
            detection_conf=detection_conf,
            ocr_conf=ocr_conf,
            vehicle_type=vehicle_type,
            timestamp=now_str
        )
        resolved_plate = resolved_entity.get("resolved_plate", plate_number)
        plate_number = resolved_plate

        # Enforce strict Indian Standard State or Bharat Series format
        is_valid_indian, fmt_type = identity_engine.validate_indian_structure(plate_number)
        if not is_valid_indian:
            print(f"[REJECTED NON-INDIAN FORMAT] Raw: {raw_text} | Normalized: {plate_number} | Format: {fmt_type}")
            return {}

        conn = get_connection()
        cursor = conn.cursor()

        # 1. Fetch camera details
        cursor.execute("SELECT * FROM cameras WHERE id = ?", (camera_id,))
        cam_row = cursor.fetchone()
        if not cam_row:
            cam_name = f"Camera {camera_id}"
            cam_sector = "Central Business District"
            cam_lat = 28.6315
            cam_lng = 77.2167
        else:
            cam_name = cam_row["name"]
            cam_sector = cam_row["sector"]
            cam_lat = cam_row["lat"]
            cam_lng = cam_row["lng"]

        # 2. Check Blacklist (Exact Match & Fuzzy OCR Similarity Match)
        cursor.execute("SELECT * FROM blacklist WHERE active = 1")
        all_blacklist_rows = cursor.fetchall()
        b_row = None
        for r in all_blacklist_rows:
            if r["plate_number"] == plate_number:
                b_row = r
                break
            else:
                sim = identity_engine.plate_similarity(plate_number, r["plate_number"])
                if sim >= 0.70:
                    b_row = r
                    plate_number = r["plate_number"]  # Correct noisy OCR variant to Watchlist target
                    break

        alert_info = None

        if b_row:
            alert_type = "BLACKLIST_MATCH"
            severity = b_row["severity"]
            desc = f"BLACKLIST TARGET DETECTED: [{b_row['category']}] Plate {plate_number} sighted at {cam_name} ({cam_sector}). Reason: {b_row['reason']}"

            cursor.execute("""
                INSERT INTO alerts (plate_number, camera_id, timestamp, alert_type, severity, description, acknowledged)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (plate_number, camera_id, now_str, alert_type, severity, desc))
            alert_id = cursor.lastrowid

            alert_info = {
                "id": alert_id,
                "plate_number": plate_number,
                "camera_id": camera_id,
                "camera_name": cam_name,
                "sector": cam_sector,
                "timestamp": now_str,
                "alert_type": alert_type,
                "severity": severity,
                "category": b_row["category"],
                "description": desc
            }

        # 3. Check Cloned Plate / Anomaly
        cursor.execute("""
            SELECT d.*, c.lat, c.lng, c.name as prev_cam_name
            FROM detections d
            JOIN cameras c ON d.camera_id = c.id
            WHERE d.plate_number = ?
            ORDER BY d.timestamp DESC LIMIT 1
        """, (plate_number,))
        prev_det = cursor.fetchone()

        if prev_det and prev_det["camera_id"] != camera_id:
            try:
                prev_time = datetime.strptime(prev_det["timestamp"], "%Y-%m-%d %H:%M:%S")
                curr_time = datetime.strptime(now_str, "%Y-%m-%d %H:%M:%S")
                dt_sec = max(1, int((curr_time - prev_time).total_seconds()))
                dist_km = haversine(prev_det["lat"], prev_det["lng"], cam_lat, cam_lng)
                calc_spd = round((dist_km / (dt_sec / 3600.0)), 1) if dt_sec > 0 else 0

                if calc_spd > 140.0:
                    anomaly_desc = f"CLONED PLATE / SPEED ANOMALY: Vehicle {plate_number} moved {round(dist_km, 1)}km in {dt_sec}s ({calc_spd} km/h) between {prev_det['prev_cam_name']} and {cam_name}."
                    cursor.execute("""
                        INSERT INTO alerts (plate_number, camera_id, timestamp, alert_type, severity, description, acknowledged)
                        VALUES (?, ?, ?, ?, ?, ?, 0)
                    """, (plate_number, camera_id, now_str, "CLONED_PLATE", "CRITICAL", anomaly_desc))
                    alert_id = cursor.lastrowid
                    alert_info = {
                        "id": alert_id,
                        "plate_number": plate_number,
                        "camera_id": camera_id,
                        "camera_name": cam_name,
                        "sector": cam_sector,
                        "timestamp": now_str,
                        "alert_type": "CLONED_PLATE",
                        "severity": "CRITICAL",
                        "description": anomaly_desc
                    }
            except Exception:
                pass

        # 4. Evaluate Downstream Reacquisition against Active Watch Queue
        reacq_eval = None
        try:
            from backend.predictive_handoff_engine import predictive_engine
            reacq_eval = predictive_engine.evaluate_reacquisition(
                incoming_plate=plate_number,
                incoming_camera_id=camera_id,
                incoming_conf=ocr_conf,
                vehicle_type=vehicle_type,
                timestamp=now_str
            )
            if reacq_eval:
                cursor.execute("""
                    INSERT INTO reacquisition_logs (handoff_id, vehicle_plate, incoming_plate, predicted_camera_id, actual_camera_id, was_correct, probability, expected_eta_sec, actual_transit_sec, eta_error_sec, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    reacq_eval["handoff_id"],
                    reacq_eval["vehicle_plate"],
                    reacq_eval["incoming_plate"],
                    reacq_eval["predicted_camera"],
                    reacq_eval["actual_camera"],
                    1 if reacq_eval["was_correct"] else 0,
                    reacq_eval["prediction_confidence"],
                    reacq_eval["expected_eta_sec"],
                    reacq_eval["actual_transit_sec"],
                    reacq_eval["eta_error_sec"],
                    now_str
                ))
        except Exception as e:
            print(f"Reacquisition eval notice: {e}")

        # 5. Generate Predictive Handoffs & Next Camera Rankings
        predictive_info = None
        created_handoffs = []
        try:
            from backend.predictive_handoff_engine import predictive_engine
            predictive_info = predictive_engine.predict_next_cameras(
                plate_number=plate_number,
                current_camera_id=camera_id,
                detection_conf=detection_conf,
                ocr_conf=ocr_conf,
                vehicle_type=vehicle_type,
                is_blacklisted=b_row is not None,
                speed_kmh=speed_kmh
            )

            created_handoffs = predictive_engine.dispatch_active_handoffs(
                plate_number=predictive_info["resolved_plate"],
                current_camera_id=camera_id,
                predictions=predictive_info["predictions"],
                is_blacklisted=b_row is not None,
                vehicle_type=vehicle_type
            )

            # Record handoffs to database
            for h in created_handoffs:
                import json
                cursor.execute("""
                    INSERT OR REPLACE INTO active_handoffs (handoff_id, vehicle_plate, source_camera_id, target_camera_id, probability, eta_min_sec, eta_max_sec, priority, status, factors_json, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    h["handoff_id"],
                    h["vehicle_plate"],
                    h["source_camera_id"],
                    h["target_camera_id"],
                    h["probability"],
                    h["eta_min_sec"],
                    h["eta_max_sec"],
                    h["priority"],
                    h["status"],
                    json.dumps(predictive_info.get("predictions", [{}])[0].get("explainability_factors", [])),
                    h["created_at"],
                    h["expires_at"]
                ))
        except Exception as e:
            print(f"Predictive handoff notice: {e}")

        # 6. Upsert Detection Record (Prevent duplicate cards for consecutive webcam frames of same vehicle)
        cursor.execute("""
            SELECT id FROM detections 
            WHERE plate_number = ? AND camera_id = ?
            ORDER BY id DESC LIMIT 1
        """, (plate_number, camera_id))
        existing_det = cursor.fetchone()

        if existing_det:
            det_id = existing_det["id"]
            cursor.execute("""
                UPDATE detections 
                SET timestamp = ?, detection_conf = ?, ocr_conf = ?, raw_text = ?
                WHERE id = ?
            """, (now_str, max(detection_conf, 0.90), max(ocr_conf, 0.90), raw_text, det_id))
        else:
            cursor.execute("""
                INSERT INTO detections (plate_number, camera_id, timestamp, detection_conf, ocr_conf, vehicle_type, speed_kmh, snapshot_path, raw_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (plate_number, camera_id, now_str, detection_conf, ocr_conf, vehicle_type, speed_kmh, snapshot_path, raw_text))
            det_id = cursor.lastrowid

        conn.commit()
        conn.close()

        resolved_plate = predictive_info["resolved_plate"] if predictive_info else plate_number
        candidate_identities = predictive_info["candidate_identities"] if predictive_info else []

        detection_payload = {
            "id": det_id,
            "plate_number": resolved_plate,
            "raw_plate": plate_number,
            "candidate_identities": candidate_identities,
            "camera_id": camera_id,
            "camera_name": cam_name,
            "sector": cam_sector,
            "lat": cam_lat,
            "lng": cam_lng,
            "timestamp": now_str,
            "detection_conf": detection_conf,
            "ocr_conf": ocr_conf,
            "vehicle_type": vehicle_type,
            "speed_kmh": speed_kmh,
            "snapshot_path": snapshot_path,
            "is_blacklisted": b_row is not None,
            "alert": alert_info,
            "predictive_info": predictive_info,
            "reacquisition_eval": reacq_eval
        }

        print(f"[SAVED TO DASHBOARD] Plate: {resolved_plate} (Raw: {plate_number}) | Node: {camera_id} | Conf: {int(ocr_conf*100)}%")

        self.broadcast_sync({
            "event": "NEW_DETECTION",
            "data": detection_payload
        })

        if alert_info:
            self.broadcast_sync({
                "event": "SECURITY_ALERT",
                "data": alert_info
            })

        if reacq_eval:
            self.broadcast_sync({
                "event": "HANDOFF_REACQUIRED",
                "data": reacq_eval
            })

        if created_handoffs:
            self.broadcast_sync({
                "event": "HANDOFF_CREATED",
                "data": {
                    "source_camera": camera_id,
                    "vehicle_plate": resolved_plate,
                    "handoffs": created_handoffs
                }
            })

        return detection_payload

    async def record_detection(
        self,
        plate_number: str,
        camera_id: str = "CAM-01",
        detection_conf: float = 0.95,
        ocr_conf: float = 0.92,
        vehicle_type: str = "Sedan",
        speed_kmh: float = 45.0,
        snapshot_path: str = "",
        raw_text: str = ""
    ) -> Dict[str, Any]:
        return self.record_detection_sync(
            plate_number=plate_number,
            camera_id=camera_id,
            detection_conf=detection_conf,
            ocr_conf=ocr_conf,
            vehicle_type=vehicle_type,
            speed_kmh=speed_kmh,
            snapshot_path=snapshot_path,
            raw_text=raw_text
        )

    async def start_background_simulation(self):
        """Simulates live city traffic stream in the background."""
        if self.simulation_running:
            return
        self.simulation_running = True

        prefixes = ["DL01AB", "DL03CB", "HR26BC", "UP16XY", "MH12CD", "KA04EF"]
        types = ["Sedan", "SUV", "Hatchback", "Truck", "Bus", "Motorcycle"]
        cameras = [f"CAM-{i:02d}" for i in range(1, 13)]

        while self.simulation_running:
            await asyncio.sleep(random.uniform(2.5, 5.0))
            try:
                # 8% chance of triggering a blacklisted vehicle sighting
                if random.random() < 0.08:
                    plate = random.choice(["DL01CA1234", "MH12AB9999", "UP16XY8888", "DL04EF5555"])
                else:
                    plate = f"{random.choice(prefixes)}{random.randint(1000, 9999)}"

                cam_id = random.choice(cameras)
                vtype = random.choice(types)
                speed = round(random.uniform(35.0, 75.0), 1)
                det_conf = round(random.uniform(0.91, 0.99), 2)
                ocr_conf = round(random.uniform(0.88, 0.98), 2)

                await self.record_detection(
                    plate_number=plate,
                    camera_id=cam_id,
                    detection_conf=det_conf,
                    ocr_conf=ocr_conf,
                    vehicle_type=vtype,
                    speed_kmh=speed
                )
            except Exception as e:
                print(f"Simulation tick error: {e}")

camera_manager = CameraManager()
