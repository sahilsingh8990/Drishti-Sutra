import sqlite3
import os
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "anpr_city.db"

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Cameras Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cameras (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            sector TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            direction TEXT NOT NULL,
            camera_type TEXT DEFAULT 'ANPR',
            status TEXT DEFAULT 'ONLINE',
            stream_url TEXT DEFAULT ''
        )
    """)

    # Detections Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT NOT NULL,
            camera_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            detection_conf REAL DEFAULT 0.95,
            ocr_conf REAL DEFAULT 0.92,
            vehicle_type TEXT DEFAULT 'Sedan',
            speed_kmh REAL DEFAULT 45.0,
            snapshot_path TEXT DEFAULT '',
            raw_text TEXT DEFAULT '',
            FOREIGN KEY (camera_id) REFERENCES cameras(id)
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_plate ON detections(plate_number)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_time ON detections(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_cam ON detections(camera_id)")

    # Blacklist Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            plate_number TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            reason TEXT NOT NULL,
            severity TEXT DEFAULT 'HIGH',
            date_added TEXT NOT NULL,
            active INTEGER DEFAULT 1
        )
    """)

    # Alerts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT NOT NULL,
            camera_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT DEFAULT 'HIGH',
            description TEXT NOT NULL,
            acknowledged INTEGER DEFAULT 0
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_plate ON alerts(plate_number)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_time ON alerts(timestamp)")

    # Vehicle Identities Table (Confidence-Aware Multi-Camera Resolution)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicle_identities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id TEXT UNIQUE,
            resolved_plate TEXT NOT NULL,
            raw_ocr_last TEXT,
            identity_confidence REAL DEFAULT 0.90,
            candidate_distribution TEXT,
            vehicle_type TEXT DEFAULT 'Sedan',
            last_camera_id TEXT,
            sightings_count INTEGER DEFAULT 1,
            first_seen TEXT,
            last_seen TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_identities_plate ON vehicle_identities(resolved_plate)")

    # Active Camera Handoffs Table (Software-Level Watch Queue)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_handoffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            handoff_id TEXT UNIQUE,
            vehicle_plate TEXT NOT NULL,
            source_camera_id TEXT NOT NULL,
            target_camera_id TEXT NOT NULL,
            probability REAL,
            eta_min_sec INTEGER,
            eta_max_sec INTEGER,
            priority TEXT DEFAULT 'NORMAL',
            status TEXT DEFAULT 'WATCHING',
            factors_json TEXT,
            created_at TEXT,
            expires_at TEXT,
            reacquired_at TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_handoffs_target ON active_handoffs(target_camera_id, status)")

    # Reacquisition Evaluation Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reacquisition_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            handoff_id TEXT,
            vehicle_plate TEXT NOT NULL,
            incoming_plate TEXT,
            predicted_camera_id TEXT,
            actual_camera_id TEXT,
            was_correct INTEGER,
            probability REAL,
            expected_eta_sec INTEGER,
            actual_transit_sec INTEGER,
            eta_error_sec INTEGER,
            timestamp TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reacq_plate ON reacquisition_logs(vehicle_plate)")

    conn.commit()
    conn.close()
    print("Database schema initialized successfully.")

if __name__ == "__main__":
    init_db()
