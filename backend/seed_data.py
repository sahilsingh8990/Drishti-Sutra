import random
import math
from datetime import datetime, timedelta
from backend.database import get_connection, init_db

CAMERAS_DATA = [
    {
        "id": "CAM-01",
        "name": "Connaught Place North Junction",
        "sector": "Central Business District",
        "lat": 28.6315,
        "lng": 77.2167,
        "direction": "Clockwise Inner",
        "camera_type": "ANPR 4K",
        "status": "ONLINE",
        "stream_url": "/static/assets/cam_sample.mp4"
    },
    {
        "id": "CAM-02",
        "name": "India Gate Hexagon Radial",
        "sector": "Administrative Zone",
        "lat": 28.6129,
        "lng": 77.2295,
        "direction": "Southbound",
        "camera_type": "ANPR Dual-Lane",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-03",
        "name": "Barakhamba Road Flyover",
        "sector": "Commercial Sector",
        "lat": 28.6289,
        "lng": 77.2270,
        "direction": "Eastbound",
        "camera_type": "ANPR 4K",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-04",
        "name": "Janpath Commercial Corridor",
        "sector": "Market Corridor",
        "lat": 28.6210,
        "lng": 77.2180,
        "direction": "Northbound",
        "camera_type": "ANPR 4K",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-05",
        "name": "Rajiv Chowk Transit Interchange",
        "sector": "Transit Hub",
        "lat": 28.6328,
        "lng": 77.2195,
        "direction": "Westbound",
        "camera_type": "ANPR Dual-Lane",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-06",
        "name": "Ring Road South Extension",
        "sector": "South Ring Corridor",
        "lat": 28.5700,
        "lng": 77.2200,
        "direction": "Southbound",
        "camera_type": "ANPR High-Speed",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-07",
        "name": "Cyber City Tech Expressway",
        "sector": "Tech Corridor",
        "lat": 28.4900,
        "lng": 77.0890,
        "direction": "Northbound",
        "camera_type": "ANPR High-Speed",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-08",
        "name": "Airport T3 Expressway Gateway",
        "sector": "Airport Sector",
        "lat": 28.5562,
        "lng": 77.1000,
        "direction": "Westbound",
        "camera_type": "ANPR High-Speed",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-09",
        "name": "Okhla Industrial Gate 2",
        "sector": "Industrial Zone",
        "lat": 28.5300,
        "lng": 77.2700,
        "direction": "Eastbound",
        "camera_type": "ANPR Heavy-Vehicle",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-10",
        "name": "DND Flyway Toll Plaza",
        "sector": "Expressway Arterial",
        "lat": 28.5800,
        "lng": 77.3000,
        "direction": "Eastbound",
        "camera_type": "ANPR High-Speed Multi-Lane",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-11",
        "name": "Delhi Gate Heritage Sector",
        "sector": "North Old Sector",
        "lat": 28.6400,
        "lng": 77.2400,
        "direction": "Northbound",
        "camera_type": "ANPR 4K",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-12",
        "name": "Ring Road Ashram Chowk",
        "sector": "Eastern Arterial",
        "lat": 28.5720,
        "lng": 77.2580,
        "direction": "Southbound",
        "camera_type": "ANPR Dual-Lane",
        "status": "ONLINE",
        "stream_url": ""
    }
]

BLACKLIST_DATA = [
    {
        "plate_number": "DL01CA1234",
        "category": "STOLEN",
        "reason": "Stolen White Honda City reported in FIR #4092/2026",
        "severity": "CRITICAL",
        "date_added": "2026-08-25 10:00:00",
        "active": 1
    },
    {
        "plate_number": "MH12AB9999",
        "category": "WANTED",
        "reason": "Vehicle linked to interstate armed burglary syndicate",
        "severity": "CRITICAL",
        "date_added": "2026-08-26 14:30:00",
        "active": 1
    },
    {
        "plate_number": "HR26DQ4321",
        "category": "SUSPICIOUS",
        "reason": "Cloned plate flagged across non-contiguous corridors",
        "severity": "HIGH",
        "date_added": "2026-08-27 09:15:00",
        "active": 1
    },
    {
        "plate_number": "UP16XY8888",
        "category": "VIOLATOR",
        "reason": "Serial red-light violator with 14 pending challans",
        "severity": "MEDIUM",
        "date_added": "2026-08-28 11:20:00",
        "active": 1
    },
    {
        "plate_number": "DL04EF5555",
        "category": "EXPIRED_DOCS",
        "reason": "Commercial vehicle operating with expired fitness & PUC",
        "severity": "MEDIUM",
        "date_added": "2026-08-29 08:45:00",
        "active": 1
    }
]

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def seed_database(force=False):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    # Check if already seeded
    cursor.execute("SELECT COUNT(*) FROM cameras")
    if cursor.fetchone()[0] > 0 and not force:
        print("Database already contains camera data. Skipping seed.")
        conn.close()
        return

    print("Seeding fresh City ANPR data...")
    cursor.execute("DELETE FROM detections")
    cursor.execute("DELETE FROM cameras")
    cursor.execute("DELETE FROM blacklist")
    cursor.execute("DELETE FROM alerts")

    # Insert Cameras
    for cam in CAMERAS_DATA:
        cursor.execute("""
            INSERT INTO cameras (id, name, sector, lat, lng, direction, camera_type, status, stream_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cam["id"], cam["name"], cam["sector"], cam["lat"], cam["lng"], cam["direction"], cam["camera_type"], cam["status"], cam["stream_url"]))

    # Insert Blacklist
    for b in BLACKLIST_DATA:
        cursor.execute("""
            INSERT INTO blacklist (plate_number, category, reason, severity, date_added, active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (b["plate_number"], b["category"], b["reason"], b["severity"], b["date_added"], b["active"]))

    # Camera map lookup
    cam_map = {c["id"]: c for c in CAMERAS_DATA}

    now = datetime.now()
    base_time = now - timedelta(hours=8)

    # 1. Detailed Trajectory: DL01CA1234 (Stolen Vehicle Track)
    # Route: CAM-11 -> CAM-01 -> CAM-04 -> CAM-02 -> CAM-12 -> CAM-10
    stolen_route = ["CAM-11", "CAM-01", "CAM-04", "CAM-02", "CAM-12", "CAM-10"]
    curr_time = base_time + timedelta(minutes=15)
    for i, cid in enumerate(stolen_route):
        speed = round(random.uniform(42.0, 58.0), 1)
        det_conf = round(random.uniform(0.92, 0.98), 2)
        ocr_conf = round(random.uniform(0.89, 0.96), 2)
        ts_str = curr_time.strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO detections (plate_number, camera_id, timestamp, detection_conf, ocr_conf, vehicle_type, speed_kmh, snapshot_path, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("DL01CA1234", cid, ts_str, det_conf, ocr_conf, "Sedan (White)", speed, "", "DL01CA1234"))

        # Create alert for blacklist match
        cursor.execute("""
            INSERT INTO alerts (plate_number, camera_id, timestamp, alert_type, severity, description, acknowledged)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("DL01CA1234", cid, ts_str, "BLACKLIST_MATCH", "CRITICAL", f"CRITICAL: Stolen vehicle DL01CA1234 spotted at {cam_map[cid]['name']} ({cam_map[cid]['sector']})", 0 if i >= len(stolen_route)-2 else 1))

        curr_time += timedelta(minutes=random.randint(7, 14))

    # 2. Detailed Trajectory: HR26DQ4321 (Speed / Cloned Plate Anomaly)
    # Route: CAM-07 (Cyber City) -> 2 mins later CAM-10 (DND Flyway) -> Distance is 25 km! Speed = 750 km/h!
    t1 = base_time + timedelta(hours=2, minutes=10)
    t2 = t1 + timedelta(minutes=2)
    cursor.execute("""
        INSERT INTO detections (plate_number, camera_id, timestamp, detection_conf, ocr_conf, vehicle_type, speed_kmh, snapshot_path, raw_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("HR26DQ4321", "CAM-07", t1.strftime("%Y-%m-%d %H:%M:%S"), 0.95, 0.93, "SUV (Black)", 65.0, "", "HR26DQ4321"))

    cursor.execute("""
        INSERT INTO detections (plate_number, camera_id, timestamp, detection_conf, ocr_conf, vehicle_type, speed_kmh, snapshot_path, raw_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("HR26DQ4321", "CAM-10", t2.strftime("%Y-%m-%d %H:%M:%S"), 0.94, 0.91, "SUV (Black)", 68.0, "", "HR26DQ4321"))

    cursor.execute("""
        INSERT INTO alerts (plate_number, camera_id, timestamp, alert_type, severity, description, acknowledged)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("HR26DQ4321", "CAM-10", t2.strftime("%Y-%m-%d %H:%M:%S"), "CLONED_PLATE", "CRITICAL", "ANOMALY: Vehicle HR26DQ4321 detected at CAM-10 only 120s after CAM-07 (Calculated Speed: 750 km/h). Suspected Cloned Plate / Teleportation!", 0))

    # 3. Detailed Trajectory: MH12AB9999 (Wanted Vehicle Track)
    # Route: CAM-08 (Airport) -> CAM-06 (South Ext) -> CAM-02 (India Gate) -> CAM-03 (Barakhamba)
    wanted_route = ["CAM-08", "CAM-06", "CAM-02", "CAM-03"]
    curr_time = base_time + timedelta(hours=3, minutes=30)
    for i, cid in enumerate(wanted_route):
        speed = round(random.uniform(50.0, 72.0), 1)
        ts_str = curr_time.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO detections (plate_number, camera_id, timestamp, detection_conf, ocr_conf, vehicle_type, speed_kmh, snapshot_path, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("MH12AB9999", cid, ts_str, 0.96, 0.94, "Luxury Sedan", speed, "", "MH12AB9999"))

        cursor.execute("""
            INSERT INTO alerts (plate_number, camera_id, timestamp, alert_type, severity, description, acknowledged)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("MH12AB9999", cid, ts_str, "BLACKLIST_MATCH", "CRITICAL", f"WANTED: Suspect vehicle MH12AB9999 sighted at {cam_map[cid]['name']}", 0 if i == len(wanted_route)-1 else 1))

        curr_time += timedelta(minutes=random.randint(10, 18))

    # 4. Generate 250+ realistic multi-vehicle detections for traffic analytics
    prefixes = ["DL03AB", "DL08CB", "HR51AK", "UP16BT", "MH02CD", "KA03MN", "DL10XY", "HR26BC", "UP14EF", "DL07JK"]
    vehicle_types = ["Sedan", "SUV", "Hatchback", "Truck", "Bus", "Motorcycle"]
    routes_pool = [
        ["CAM-01", "CAM-03", "CAM-11"],
        ["CAM-07", "CAM-08", "CAM-06", "CAM-02"],
        ["CAM-09", "CAM-12", "CAM-10"],
        ["CAM-05", "CAM-01", "CAM-04", "CAM-02"],
        ["CAM-10", "CAM-12", "CAM-06", "CAM-08"],
        ["CAM-11", "CAM-05", "CAM-01", "CAM-04"]
    ]

    for p_idx in range(50):
        plate = f"{random.choice(prefixes)}{random.randint(1000, 9999)}"
        vtype = random.choice(vehicle_types)
        route = random.choice(routes_pool)
        route_start = base_time + timedelta(minutes=random.randint(0, 420))

        step_time = route_start
        for cid in route:
            det_conf = round(random.uniform(0.88, 0.99), 2)
            ocr_conf = round(random.uniform(0.85, 0.98), 2)
            speed = round(random.uniform(30.0, 75.0), 1)
            cursor.execute("""
                INSERT INTO detections (plate_number, camera_id, timestamp, detection_conf, ocr_conf, vehicle_type, speed_kmh, snapshot_path, raw_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (plate, cid, step_time.strftime("%Y-%m-%d %H:%M:%S"), det_conf, ocr_conf, vtype, speed, "", plate))
            step_time += timedelta(minutes=random.randint(5, 20))

    conn.commit()
    conn.close()
    print("City ANPR simulation dataset seeded successfully!")

if __name__ == "__main__":
    seed_database(force=True)
