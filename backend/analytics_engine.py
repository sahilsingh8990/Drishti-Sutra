from collections import defaultdict
from datetime import datetime
from backend.database import get_connection

def get_overview_kpis():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM detections")
    total_detections = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT plate_number) FROM detections")
    unique_vehicles = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM cameras WHERE status = 'ONLINE'")
    active_cameras = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM cameras")
    total_cameras = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM alerts WHERE acknowledged = 0")
    active_alerts = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(speed_kmh) FROM detections")
    avg_speed_row = cursor.fetchone()[0]
    avg_speed = round(avg_speed_row, 1) if avg_speed_row else 45.0

    # Congestion Index based on camera load
    cursor.execute("""
        SELECT camera_id, COUNT(*) as cnt
        FROM detections
        GROUP BY camera_id
    """)
    loads = [r["cnt"] for r in cursor.fetchall()]
    max_load = max(loads) if loads else 1
    avg_load = sum(loads) / len(loads) if loads else 0
    congestion_index = min(100, int((avg_load / (max_load * 0.8 if max_load > 0 else 1)) * 65))

    conn.close()

    return {
        "total_detections": total_detections,
        "unique_vehicles": unique_vehicles,
        "active_cameras": active_cameras,
        "total_cameras": total_cameras,
        "active_alerts": active_alerts,
        "avg_speed_kmh": avg_speed,
        "congestion_index": congestion_index
    }

def get_traffic_density_heatmap():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.id, c.name, c.sector, c.lat, c.lng, c.direction, c.status,
               COUNT(d.id) AS detection_count,
               AVG(d.speed_kmh) AS avg_speed
        FROM cameras c
        LEFT JOIN detections d ON c.id = d.camera_id
        GROUP BY c.id
    """)
    rows = cursor.fetchall()
    conn.close()

    max_count = max([r["detection_count"] for r in rows]) if rows else 1

    heatmap_points = []
    camera_nodes = []

    for r in rows:
        count = r["detection_count"]
        # Normalize weight between 0.2 and 1.0 for Leaflet.heat
        weight = round(max(0.2, count / max_count), 2) if max_count > 0 else 0.5
        heatmap_points.append([r["lat"], r["lng"], weight])

        avg_spd = round(r["avg_speed"], 1) if r["avg_speed"] else 50.0

        if count >= max_count * 0.75:
            congestion_level = "Severe Congestion"
            status_color = "red"
        elif count >= max_count * 0.45:
            congestion_level = "Moderate Congestion"
            status_color = "amber"
        else:
            congestion_level = "Free Flow"
            status_color = "emerald"

        camera_nodes.append({
            "id": r["id"],
            "name": r["name"],
            "sector": r["sector"],
            "lat": r["lat"],
            "lng": r["lng"],
            "direction": r["direction"],
            "status": r["status"],
            "detection_count": count,
            "avg_speed": avg_spd,
            "congestion_level": congestion_level,
            "status_color": status_color,
            "intensity": weight
        })

    return {
        "heatmap_points": heatmap_points,
        "camera_nodes": camera_nodes
    }

def get_od_matrix():
    """
    Origin-Destination macro mobility analysis.
    Identifies the entry sector (origin) and exit sector (destination) for each vehicle.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT d.plate_number, d.timestamp, c.sector
        FROM detections d
        JOIN cameras c ON d.camera_id = c.id
        ORDER BY d.plate_number, d.timestamp ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    vehicle_trips = defaultdict(list)
    for r in rows:
        vehicle_trips[r["plate_number"]].append(r["sector"])

    od_counts = defaultdict(int)
    all_sectors = set()

    for plate, sectors in vehicle_trips.items():
        if len(sectors) >= 1:
            origin = sectors[0]
            destination = sectors[-1] if len(sectors) > 1 else sectors[0]
            od_counts[(origin, destination)] += 1
            all_sectors.add(origin)
            all_sectors.add(destination)

    sorted_sectors = sorted(list(all_sectors))

    # Build matrix
    matrix = []
    for orig in sorted_sectors:
        row = {"origin": orig, "destinations": {}}
        for dest in sorted_sectors:
            row["destinations"][dest] = od_counts.get((orig, dest), 0)
        matrix.append(row)

    # Top corridors
    corridors = []
    for (orig, dest), count in sorted(od_counts.items(), key=lambda x: x[1], reverse=True):
        if orig != dest:
            corridors.append({
                "origin": orig,
                "destination": dest,
                "volume": count
            })

    return {
        "sectors": sorted_sectors,
        "matrix": matrix,
        "top_corridors": corridors[:8]
    }

def get_congestion_bottlenecks():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.id, c.name, c.sector, c.lat, c.lng,
               COUNT(d.id) AS total_vehicles,
               AVG(d.speed_kmh) AS avg_speed
        FROM cameras c
        LEFT JOIN detections d ON c.id = d.camera_id
        GROUP BY c.id
        ORDER BY total_vehicles DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    bottlenecks = []
    for r in rows:
        vol = r["total_vehicles"]
        spd = round(r["avg_speed"], 1) if r["avg_speed"] else 45.0
        # Bottleneck index: high volume + low speed = higher index
        speed_factor = max(10, 80 - spd) / 80.0
        risk_score = min(100, int((vol * 3.5) * speed_factor))

        if risk_score > 70:
            level = "Severe Bottleneck"
            badge = "bg-red-500/20 text-red-400 border-red-500/40"
        elif risk_score > 40:
            level = "Moderate Congestion"
            badge = "bg-amber-500/20 text-amber-400 border-amber-500/40"
        else:
            level = "Smooth Flow"
            badge = "bg-emerald-500/20 text-emerald-400 border-emerald-500/40"

        bottlenecks.append({
            "camera_id": r["id"],
            "camera_name": r["name"],
            "sector": r["sector"],
            "lat": r["lat"],
            "lng": r["lng"],
            "total_vehicles": vol,
            "avg_speed": spd,
            "risk_score": risk_score,
            "level": level,
            "badge": badge
        })

    return sorted(bottlenecks, key=lambda x: x["risk_score"], reverse=True)

def get_hourly_volume_trends():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT strftime('%H', timestamp) AS hour_str, COUNT(*) as cnt
        FROM detections
        GROUP BY hour_str
        ORDER BY hour_str ASC
    """)
    hour_rows = cursor.fetchall()

    hourly_dict = {f"{h:02d}:00": 0 for h in range(24)}
    for r in hour_rows:
        if r["hour_str"]:
            hourly_dict[f"{int(r['hour_str']):02d}:00"] = r["cnt"]

    # Vehicle types distribution
    cursor.execute("""
        SELECT vehicle_type, COUNT(*) as cnt
        FROM detections
        GROUP BY vehicle_type
        ORDER BY cnt DESC
    """)
    type_rows = cursor.fetchall()
    vtypes = {r["vehicle_type"]: r["cnt"] for r in type_rows}

    conn.close()

    return {
        "hours": list(hourly_dict.keys()),
        "volumes": list(hourly_dict.values()),
        "vehicle_types": vtypes
    }

if __name__ == "__main__":
    print("KPIs:", get_overview_kpis())
    print("OD Corridors:", get_od_matrix()["top_corridors"][:3])
