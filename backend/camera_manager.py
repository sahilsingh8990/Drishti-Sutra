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

    async def record_detection(
        self,
        plate_number: str,
        camera_id: str,
        detection_conf: float = 0.95,
        ocr_conf: float = 0.92,
        vehicle_type: str = "Sedan",
        speed_kmh: float = 45.0,
        snapshot_path: str = "",
        raw_text: str = ""
    ) -> Dict[str, Any]:
        """
        Ingests a detection from live ANPR camera or simulation, checks for blacklist and anomaly alerts,
        and broadcasts to all connected clients in real-time.
        """
        plate_number = plate_number.strip().upper()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_connection()
        cursor = conn.cursor()

        # 1. Fetch camera details
        cursor.execute("SELECT * FROM cameras WHERE id = ?", (camera_id,))
        cam_row = cursor.fetchone()
        if not cam_row:
            # Fallback default if camera doesn't exist
            cam_name = f"Camera {camera_id}"
            cam_sector = "Metro Grid"
            cam_lat = 28.6139
            cam_lng = 77.2090
        else:
            cam_name = cam_row["name"]
            cam_sector = cam_row["sector"]
            cam_lat = cam_row["lat"]
            cam_lng = cam_row["lng"]

        # 2. Check Blacklist
        cursor.execute("SELECT * FROM blacklist WHERE plate_number = ? AND active = 1", (plate_number,))
        b_row = cursor.fetchone()
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

        # 3. Check Cloned Plate / Impossible Speed Anomaly against last detection
        cursor.execute("""
            SELECT d.*, c.lat, c.lng, c.name as prev_cam_name
            FROM detections d
            JOIN cameras c ON d.camera_id = c.id
            WHERE d.plate_number = ?
            ORDER BY d.timestamp DESC LIMIT 1
        """, (plate_number,))
        prev_det = cursor.fetchone()

        if prev_det and prev_det["camera_id"] != camera_id:
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

        # 4. Insert Detection
        cursor.execute("""
            INSERT INTO detections (plate_number, camera_id, timestamp, detection_conf, ocr_conf, vehicle_type, speed_kmh, snapshot_path, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (plate_number, camera_id, now_str, detection_conf, ocr_conf, vehicle_type, speed_kmh, snapshot_path, raw_text))
        det_id = cursor.lastrowid

        conn.commit()
        conn.close()

        detection_payload = {
            "id": det_id,
            "plate_number": plate_number,
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
            "alert": alert_info
        }

        # Broadcast via WebSocket
        await self.broadcast({
            "event": "NEW_DETECTION",
            "data": detection_payload
        })

        if alert_info:
            await self.broadcast({
                "event": "SECURITY_ALERT",
                "data": alert_info
            })

        return detection_payload

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
