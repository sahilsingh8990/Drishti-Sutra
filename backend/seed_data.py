import random
import math
from datetime import datetime, timedelta
from backend.database import get_connection, init_db

CAMERAS_DATA = [
    {
        "id": "CAM-01",
        "name": "Sitabuldi Central Interchange",
        "sector": "Central Business District",
        "lat": 21.1458,
        "lng": 79.0882,
        "direction": "Clockwise Inner",
        "camera_type": "ANPR 4K",
        "status": "ONLINE",
        "stream_url": "/static/assets/cam_sample.mp4"
    },
    {
        "id": "CAM-02",
        "name": "Zero Mile Freedom Park Square",
        "sector": "Heritage Zone",
        "lat": 21.1495,
        "lng": 79.0886,
        "direction": "Northbound",
        "camera_type": "ANPR Dual-Lane",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-03",
        "name": "Nagpur Railway Station Main Square",
        "sector": "Transit Sector",
        "lat": 21.1524,
        "lng": 79.0887,
        "direction": "Eastbound",
        "camera_type": "ANPR 4K",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-04",
        "name": "Wardha Road Airport Flyover",
        "sector": "Airport Corridor",
        "lat": 21.0922,
        "lng": 79.0617,
        "direction": "Southbound",
        "camera_type": "ANPR 4K",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-05",
        "name": "Sadar Commercial Square",
        "sector": "Commercial Sector",
        "lat": 21.1648,
        "lng": 79.0818,
        "direction": "Westbound",
        "camera_type": "ANPR Dual-Lane",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-06",
        "name": "Kamptee Road Automotive Square",
        "sector": "North Arterial Corridor",
        "lat": 21.1873,
        "lng": 79.0984,
        "direction": "Northbound",
        "camera_type": "ANPR High-Speed",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-07",
        "name": "Shankar Nagar Square",
        "sector": "West Sector",
        "lat": 21.1378,
        "lng": 79.0632,
        "direction": "Southwest",
        "camera_type": "ANPR High-Speed",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-08",
        "name": "Law College Square / Amravati Rd",
        "sector": "University Corridor",
        "lat": 21.1462,
        "lng": 79.0543,
        "direction": "Westbound",
        "camera_type": "ANPR High-Speed",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-09",
        "name": "Medical College Square",
        "sector": "Medical Zone",
        "lat": 21.1302,
        "lng": 79.0965,
        "direction": "Southeast",
        "camera_type": "ANPR Heavy-Vehicle",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-10",
        "name": "Cotton Market Square",
        "sector": "Eastern Market Sector",
        "lat": 21.1425,
        "lng": 79.0912,
        "direction": "Eastbound",
        "camera_type": "ANPR High-Speed Multi-Lane",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-11",
        "name": "Mankapur Ring Road Square",
        "sector": "Outer Ring North",
        "lat": 21.1895,
        "lng": 79.0694,
        "direction": "Northbound",
        "camera_type": "ANPR 4K",
        "status": "ONLINE",
        "stream_url": ""
    },
    {
        "id": "CAM-12",
        "name": "Rahate Colony Square",
        "sector": "South Central Sector",
        "lat": 21.1278,
        "lng": 79.0768,
        "direction": "Southbound",
        "camera_type": "ANPR Dual-Lane",
        "status": "ONLINE",
        "stream_url": ""
    }
]

# Physical Road Network Graph Adjacency for Nagpur Squares
GRAPH_ADJACENCY = {
    "CAM-01": ["CAM-02", "CAM-03", "CAM-05", "CAM-07", "CAM-10", "CAM-12"],
    "CAM-02": ["CAM-01", "CAM-03", "CAM-05", "CAM-11"],
    "CAM-03": ["CAM-01", "CAM-02", "CAM-10"],
    "CAM-04": ["CAM-07", "CAM-09", "CAM-12"],
    "CAM-05": ["CAM-01", "CAM-02", "CAM-06", "CAM-08"],
    "CAM-06": ["CAM-05", "CAM-11"],
    "CAM-07": ["CAM-01", "CAM-04", "CAM-08"],
    "CAM-08": ["CAM-05", "CAM-07", "CAM-11"],
    "CAM-09": ["CAM-04", "CAM-10", "CAM-12"],
    "CAM-10": ["CAM-01", "CAM-03", "CAM-09"],
    "CAM-11": ["CAM-02", "CAM-06", "CAM-08"],
    "CAM-12": ["CAM-01", "CAM-04", "CAM-09"]
}

# 15 Blacklisted Security Watchlist Data (Nagpur Jurisdictions)
EXPLICIT_BLACKLIST_DATA = [
    {
        "plate_number": "MH49AE2355",
        "category": "STOLEN",
        "reason": "Stolen White Honda City reported in Nagpur Sitabuldi PS FIR #4092/2026",
        "severity": "CRITICAL",
        "date_added": "2026-08-25 10:00:00"
    },
    {
        "plate_number": "MH31AB9999",
        "category": "WANTED",
        "reason": "Vehicle linked to Nagpur Wardha Road armed robbery syndicate",
        "severity": "CRITICAL",
        "date_added": "2026-08-26 14:30:00"
    },
    {
        "plate_number": "MH31DQ4321",
        "category": "SUSPICIOUS",
        "reason": "Cloned plate flagged across non-contiguous corridors in Nagpur",
        "severity": "HIGH",
        "date_added": "2026-08-27 09:15:00"
    },
    {
        "plate_number": "MH40XY8888",
        "category": "VIOLATOR",
        "reason": "Serial red-light violator with 14 pending challans across Sadar Square",
        "severity": "MEDIUM",
        "date_added": "2026-08-28 11:20:00"
    },
    {
        "plate_number": "25BH2534O",
        "category": "EXPIRED_DOCS",
        "reason": "Bharat series vehicle operating with expired fitness & PUC on Amravati Rd",
        "severity": "MEDIUM",
        "date_added": "2026-08-29 08:45:00"
    },
    {
        "plate_number": "MH31BW1001",
        "category": "STOLEN",
        "reason": "Stolen Black Hyundai Creta reported in Sadar PS FIR #1024/2026",
        "severity": "CRITICAL",
        "date_added": "2026-08-25 12:15:00"
    },
    {
        "plate_number": "MH49CD2045",
        "category": "WANTED",
        "reason": "Wanted suspect vehicle in Lakadganj commercial burglary",
        "severity": "CRITICAL",
        "date_added": "2026-08-26 16:20:00"
    },
    {
        "plate_number": "MH40EF3090",
        "category": "SUSPICIOUS",
        "reason": "Suspicious vehicle linked to Mankapur night illegal transport",
        "severity": "HIGH",
        "date_added": "2026-08-27 18:40:00"
    },
    {
        "plate_number": "MH12GH4012",
        "category": "VIOLATOR",
        "reason": "Serial speed violator (95 km/h in 50 km/h Wardha Flyover zone)",
        "severity": "MEDIUM",
        "date_added": "2026-08-28 08:10:00"
    },
    {
        "plate_number": "MH01JK5080",
        "category": "EXPIRED_DOCS",
        "reason": "Commercial heavy truck with revoked permit at Automotive Square",
        "severity": "MEDIUM",
        "date_added": "2026-08-29 11:30:00"
    },
    {
        "plate_number": "MH02LM6020",
        "category": "STOLEN",
        "reason": "Stolen Silver Maruti Swift reported in Dhantoli PS FIR #892/2026",
        "severity": "CRITICAL",
        "date_added": "2026-08-25 15:45:00"
    },
    {
        "plate_number": "MH04NP7035",
        "category": "WANTED",
        "reason": "Wanted suspect vehicle in Cotton Market extortion case",
        "severity": "CRITICAL",
        "date_added": "2026-08-26 20:10:00"
    },
    {
        "plate_number": "MH14RS8044",
        "category": "SUSPICIOUS",
        "reason": "Vehicle carrying counterfeit registration plates across Kamptee Rd",
        "severity": "HIGH",
        "date_added": "2026-08-27 22:15:00"
    },
    {
        "plate_number": "24BH9011X",
        "category": "VIOLATOR",
        "reason": "Bharat Series car flagged for 18 unpaid toll violations at Sitabuldi",
        "severity": "MEDIUM",
        "date_added": "2026-08-28 14:50:00"
    },
    {
        "plate_number": "CG04TU1122",
        "category": "EXPIRED_DOCS",
        "reason": "Interstate commercial vehicle operating with expired hazmat permit",
        "severity": "HIGH",
        "date_added": "2026-08-29 17:05:00"
    }
]

VEHICLE_TYPES = [
    "Sedan (White)", "SUV (Black)", "Hatchback (Grey)", "Luxury Sedan (Silver)",
    "Commercial Truck", "Motorcycle (Red)", "Sedan (Blue)", "SUV (White)", "Delivery Van"
]

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def generate_150_unique_plates():
    # 15 explicit blacklisted plates
    bl_plates = [b["plate_number"] for b in EXPLICIT_BLACKLIST_DATA]
    plates_set = set(bl_plates)

    rto_prefixes = [
        "MH31", "MH49", "MH40", "MH12", "MH01", "MH02", "MH04", "MH14", "MH15", "MH20",
        "DL01", "DL03", "KA03", "CG04", "MP09", "GJ01"
    ]
    series_letters = ["AB", "AE", "BC", "CD", "DQ", "EF", "GH", "JK", "LM", "NP", "RS", "TU", "XY", "ZZ"]

    rng = random.Random(42) # Fixed seed for reproducible dataset

    while len(plates_set) < 150:
        if rng.random() < 0.15:
            # Generate Bharat Series plate
            yr = rng.choice([23, 24, 25])
            num = rng.randint(1000, 9999)
            let = rng.choice(["A", "B", "C", "D", "E", "O", "X"])
            p = f"{yr}BH{num}{let}"
        else:
            rto = rng.choice(rto_prefixes)
            series = rng.choice(series_letters)
            num = rng.randint(1000, 9999)
            p = f"{rto}{series}{num}"
        plates_set.add(p)

    return list(plates_set)

def seed_database(force=False):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM cameras")
    if cursor.fetchone()[0] > 0 and not force:
        print("Database already contains camera data. Skipping seed.")
        conn.close()
        return

    print("Generating Artificial Dataset: 150 Vehicles & 15 Blacklisted Vehicles across Nagpur Squares...")
    cursor.execute("DELETE FROM detections")
    cursor.execute("DELETE FROM cameras")
    cursor.execute("DELETE FROM blacklist")
    cursor.execute("DELETE FROM alerts")
    cursor.execute("DELETE FROM active_handoffs")
    cursor.execute("DELETE FROM reacquisition_logs")

    # 1. Insert Cameras
    for cam in CAMERAS_DATA:
        cursor.execute("""
            INSERT INTO cameras (id, name, sector, lat, lng, direction, camera_type, status, stream_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cam["id"], cam["name"], cam["sector"], cam["lat"], cam["lng"], cam["direction"], cam["camera_type"], cam["status"], cam["stream_url"]))

    # 2. Insert 15 Blacklisted Vehicles
    bl_map = {}
    for b in EXPLICIT_BLACKLIST_DATA:
        cursor.execute("""
            INSERT INTO blacklist (plate_number, category, reason, severity, date_added, active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (b["plate_number"], b["category"], b["reason"], b["severity"], b["date_added"]))
        bl_map[b["plate_number"]] = b

    cam_map = {c["id"]: c for c in CAMERAS_DATA}
    all_150_plates = generate_150_unique_plates()

    now = datetime.now()
    base_time = now - timedelta(hours=24) # 24-hour simulation window

    rng = random.Random(2026)

    total_detections_count = 0
    total_alerts_count = 0

    # 3. Generate Realistic Trajectories for all 150 Vehicles
    for p_idx, plate in enumerate(all_150_plates):
        vtype = rng.choice(VEHICLE_TYPES)
        is_bl = plate in bl_map

        # Choose route length (3 to 8 checkpoints)
        route_len = rng.randint(3, 8) if is_bl else rng.randint(3, 6)

        # Pick random starting node
        start_node = rng.choice(list(GRAPH_ADJACENCY.keys()))
        route = [start_node]

        # Random walk along physical road graph
        while len(route) < route_len:
            curr_node = route[-1]
            neighbors = GRAPH_ADJACENCY[curr_node]
            # avoid immediate backtracking if possible
            valid_next = [n for n in neighbors if len(route) < 2 or n != route[-2]]
            next_node = rng.choice(valid_next if valid_next else neighbors)
            route.append(next_node)

        # Distribute departure time across 24h with peak traffic weightings
        # Morning peak (8-11), Evening peak (17-20)
        hour_slot = rng.choices(
            population=list(range(24)),
            weights=[1, 1, 1, 1, 2, 3, 5, 8, 12, 10, 8, 7, 7, 7, 8, 9, 11, 13, 12, 9, 6, 4, 2, 1],
            k=1
        )[0]

        start_ts = base_time + timedelta(hours=hour_slot, minutes=rng.randint(0, 59))
        step_ts = start_ts

        for step_i, cid in enumerate(route):
            speed = round(rng.uniform(32.0, 76.0), 1)
            det_conf = round(rng.uniform(0.91, 0.99), 2)
            ocr_conf = round(rng.uniform(0.88, 0.98), 2)
            ts_str = step_ts.strftime("%Y-%m-%d %H:%M:%S")

            # OCR confusion simulation on non-critical frames for realism
            raw_text = plate
            if rng.random() < 0.15:
                raw_text = plate.replace("B", "8").replace("O", "0").replace("Z", "2")

            cursor.execute("""
                INSERT INTO detections (plate_number, camera_id, timestamp, detection_conf, ocr_conf, vehicle_type, speed_kmh, snapshot_path, raw_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (plate, cid, ts_str, det_conf, ocr_conf, vtype, speed, "", raw_text))

            total_detections_count += 1

            # Trigger security alert if vehicle is blacklisted
            if is_bl:
                bl_info = bl_map[plate]
                cursor.execute("""
                    INSERT INTO alerts (plate_number, camera_id, timestamp, alert_type, severity, description, acknowledged)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    plate, cid, ts_str,
                    "BLACKLIST_MATCH",
                    bl_info["severity"],
                    f"{bl_info['severity']}: Blacklisted vehicle {plate} ({bl_info['category']}) spotted at {cam_map[cid]['name']} ({cam_map[cid]['sector']})",
                    0 if step_i >= len(route) - 2 else 1
                ))
                total_alerts_count += 1

            # Time progression between nodes (4 to 16 mins)
            step_ts += timedelta(minutes=rng.randint(4, 16))

    # 4. Seed Active Handoffs for Blacklisted & Top Active Tracks
    cursor.execute("""
        INSERT INTO active_handoffs (handoff_id, vehicle_plate, source_camera_id, target_camera_id, probability, eta_min_sec, eta_max_sec, priority, status, factors_json, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "HDF-MH49AE2355-CAM-04-01",
        "MH49AE2355",
        "CAM-01",
        "CAM-04",
        0.78,
        180,
        360,
        "CRITICAL",
        "WATCHING",
        '[{"factor_name": "Security Watchlist Handoff Override", "score": "PRIORITY 1"}, {"factor_name": "Historical Transition Frequency", "score": "78%"}]',
        now.strftime("%Y-%m-%d %H:%M:%S"),
        (now + timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M:%S")
    ))

    cursor.execute("""
        INSERT INTO active_handoffs (handoff_id, vehicle_plate, source_camera_id, target_camera_id, probability, eta_min_sec, eta_max_sec, priority, status, factors_json, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "HDF-MH31AB9999-CAM-03-01",
        "MH31AB9999",
        "CAM-02",
        "CAM-03",
        0.82,
        240,
        480,
        "CRITICAL",
        "WATCHING",
        '[{"factor_name": "Security Watchlist Handoff Override", "score": "PRIORITY 1"}, {"factor_name": "Shortest Path Transit", "score": "1.1 km"}]',
        now.strftime("%Y-%m-%d %H:%M:%S"),
        (now + timedelta(minutes=25)).strftime("%Y-%m-%d %H:%M:%S")
    ))

    # 5. Seed Reacquisition Accuracy Logs
    reacq_samples = [
        ("HDF-MH49AE2355-CAM-04-01", "MH49AE2355", "MH49AE2355", "CAM-04", "CAM-04", 1, 0.78, 210, 195, -15, (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")),
        ("HDF-MH31AB9999-CAM-03-01", "MH31AB9999", "MH31AB9999", "CAM-03", "CAM-03", 1, 0.82, 320, 310, -10, (now - timedelta(hours=2, minutes=45)).strftime("%Y-%m-%d %H:%M:%S")),
        ("HDF-MH31DQ4321-CAM-10-01", "MH31DQ4321", "MH31DQ4321", "CAM-08", "CAM-10", 0, 0.35, 600, 120, -480, (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")),
        ("HDF-25BH2534O-CAM-04-01", "25BH2534O", "25BH25340", "CAM-04", "CAM-04", 1, 0.72, 280, 290, 10, (now - timedelta(hours=1, minutes=30)).strftime("%Y-%m-%d %H:%M:%S")),
        ("HDF-MH40XY8888-CAM-02-01", "MH40XY8888", "MH40XY8888", "CAM-02", "CAM-02", 1, 0.88, 420, 415, -5, (now - timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M:%S"))
    ]

    for r in reacq_samples:
        cursor.execute("""
            INSERT INTO reacquisition_logs (handoff_id, vehicle_plate, incoming_plate, predicted_camera_id, actual_camera_id, was_correct, probability, expected_eta_sec, actual_transit_sec, eta_error_sec, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, r)

    conn.commit()
    conn.close()
    print(f"Artificial Dataset Generated Successfully: {len(all_150_plates)} unique vehicles ({len(EXPLICIT_BLACKLIST_DATA)} blacklisted), {total_detections_count} detections across 12 Nagpur squares.")

if __name__ == "__main__":
    seed_database(force=True)
