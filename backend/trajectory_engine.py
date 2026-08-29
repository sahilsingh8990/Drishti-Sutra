import math
from datetime import datetime
from backend.database import get_connection

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def reconstruct_trajectory(plate_number: str, start_time: str = None, end_time: str = None):
    """
    Reconstructs the chronological spatio-temporal trajectory of a vehicle across all city ANPR cameras.
    """
    plate_number = plate_number.strip().upper()
    conn = get_connection()
    cursor = conn.cursor()

    # Check blacklist status
    cursor.execute("SELECT * FROM blacklist WHERE plate_number = ?", (plate_number,))
    blacklist_row = cursor.fetchone()
    blacklist_info = dict(blacklist_row) if blacklist_row else None

    query = """
        SELECT d.*, c.name AS camera_name, c.sector, c.lat, c.lng, c.direction, c.camera_type
        FROM detections d
        JOIN cameras c ON d.camera_id = c.id
        WHERE d.plate_number = ?
    """
    params = [plate_number]

    if start_time:
        query += " AND d.timestamp >= ?"
        params.append(start_time)
    if end_time:
        query += " AND d.timestamp <= ?"
        params.append(end_time)

    query += " ORDER BY d.timestamp ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {
            "found": False,
            "plate_number": plate_number,
            "message": f"No detection records found for vehicle plate '{plate_number}'",
            "waypoints": [],
            "summary": None,
            "blacklist_info": blacklist_info
        }

    waypoints = []
    total_distance_km = 0.0
    anomalies = []

    for i, row in enumerate(rows):
        r_dict = dict(row)
        current_time = datetime.strptime(r_dict["timestamp"], "%Y-%m-%d %H:%M:%S")

        leg_distance_km = 0.0
        leg_duration_seconds = 0
        leg_speed_kmh = 0.0
        is_anomaly = False
        anomaly_reason = ""

        if i > 0:
            prev_wp = waypoints[i - 1]
            prev_time = datetime.strptime(prev_wp["timestamp"], "%Y-%m-%d %H:%M:%S")
            prev_lat, prev_lng = prev_wp["lat"], prev_wp["lng"]

            leg_distance_km = haversine(prev_lat, prev_lng, r_dict["lat"], r_dict["lng"])
            total_distance_km += leg_distance_km

            leg_duration_seconds = max(1, int((current_time - prev_time).total_seconds()))
            leg_duration_hours = leg_duration_seconds / 3600.0

            if leg_duration_hours > 0:
                leg_speed_kmh = round(leg_distance_km / leg_duration_hours, 1)

            # Anomaly Checks
            if leg_speed_kmh > 140.0:
                is_anomaly = True
                anomaly_reason = f"Impossible Transit Speed ({leg_speed_kmh} km/h) over {round(leg_distance_km, 1)}km in {leg_duration_seconds}s. Suspected Cloned Plate or System Timestamp Discrepancy."
                anomalies.append({
                    "type": "IMPOSSIBLE_SPEED_OR_CLONED_PLATE",
                    "from_camera": prev_wp["camera_name"],
                    "to_camera": r_dict["camera_name"],
                    "distance_km": round(leg_distance_km, 2),
                    "duration_seconds": leg_duration_seconds,
                    "calculated_speed_kmh": leg_speed_kmh,
                    "timestamp": r_dict["timestamp"]
                })

        wp = {
            "step": i + 1,
            "detection_id": r_dict["id"],
            "camera_id": r_dict["camera_id"],
            "camera_name": r_dict["camera_name"],
            "sector": r_dict["sector"],
            "lat": r_dict["lat"],
            "lng": r_dict["lng"],
            "direction": r_dict["direction"],
            "timestamp": r_dict["timestamp"],
            "detection_conf": r_dict["detection_conf"],
            "ocr_conf": r_dict["ocr_conf"],
            "vehicle_type": r_dict["vehicle_type"],
            "instant_speed_kmh": r_dict["speed_kmh"],
            "leg_distance_km": round(leg_distance_km, 2),
            "leg_duration_seconds": leg_duration_seconds,
            "leg_speed_kmh": leg_speed_kmh,
            "is_anomaly": is_anomaly,
            "anomaly_reason": anomaly_reason,
            "snapshot_path": r_dict["snapshot_path"]
        }
        waypoints.append(wp)

    first_time = datetime.strptime(waypoints[0]["timestamp"], "%Y-%m-%d %H:%M:%S")
    last_time = datetime.strptime(waypoints[-1]["timestamp"], "%Y-%m-%d %H:%M:%S")
    total_elapsed_seconds = int((last_time - first_time).total_seconds())
    total_elapsed_hours = total_elapsed_seconds / 3600.0
    avg_speed_kmh = round(total_distance_km / total_elapsed_hours, 1) if total_elapsed_hours > 0 else 0.0

    summary = {
        "plate_number": plate_number,
        "total_sightings": len(waypoints),
        "total_distance_km": round(total_distance_km, 2),
        "total_elapsed_minutes": round(total_elapsed_seconds / 60.0, 1),
        "avg_speed_kmh": avg_speed_kmh,
        "first_seen": {
            "camera_id": waypoints[0]["camera_id"],
            "camera_name": waypoints[0]["camera_name"],
            "sector": waypoints[0]["sector"],
            "timestamp": waypoints[0]["timestamp"]
        },
        "last_seen": {
            "camera_id": waypoints[-1]["camera_id"],
            "camera_name": waypoints[-1]["camera_name"],
            "sector": waypoints[-1]["sector"],
            "timestamp": waypoints[-1]["timestamp"]
        },
        "vehicle_type": waypoints[-1]["vehicle_type"],
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "is_blacklisted": blacklist_info is not None,
        "blacklist_info": blacklist_info
    }

    return {
        "found": True,
        "plate_number": plate_number,
        "summary": summary,
        "waypoints": waypoints
    }

if __name__ == "__main__":
    test_res = reconstruct_trajectory("DL01CA1234")
    print("Trajectory reconstruction test result:")
    print("Found:", test_res["found"])
    print("Summary:", test_res["summary"])
