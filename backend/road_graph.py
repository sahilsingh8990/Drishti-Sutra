import math
from typing import List, Dict, Any, Tuple, Optional, Set
from backend.trajectory_engine import haversine

# ============================================================
# ROAD NETWORK GRAPH: NODES & JUNCTIONS
# ============================================================

CAMERA_NODES = {
    "CAM-01": {
        "id": "CAM-01",
        "name": "Sitabuldi Central Interchange",
        "sector": "Central Business District",
        "lat": 21.1458,
        "lng": 79.0882,
        "direction": "Clockwise Inner",
        "is_camera": True,
        "status": "ONLINE"
    },
    "CAM-02": {
        "id": "CAM-02",
        "name": "Zero Mile Freedom Park Square",
        "sector": "Heritage Zone",
        "lat": 21.1495,
        "lng": 79.0886,
        "direction": "Northbound",
        "is_camera": True,
        "status": "ONLINE"
    },
    "CAM-03": {
        "id": "CAM-03",
        "name": "Nagpur Railway Station Main Square",
        "sector": "Transit Sector",
        "lat": 21.1524,
        "lng": 79.0887,
        "direction": "Eastbound",
        "is_camera": True,
        "status": "ONLINE"
    },
    "CAM-04": {
        "id": "CAM-04",
        "name": "Wardha Road Airport Flyover",
        "sector": "Airport Corridor",
        "lat": 21.0922,
        "lng": 79.0617,
        "direction": "Southbound",
        "is_camera": True,
        "status": "ONLINE"
    },
    "CAM-05": {
        "id": "CAM-05",
        "name": "Sadar Commercial Square",
        "sector": "Commercial Sector",
        "lat": 21.1648,
        "lng": 79.0818,
        "direction": "Westbound",
        "is_camera": True,
        "status": "ONLINE"
    },
    "CAM-06": {
        "id": "CAM-06",
        "name": "Kamptee Road Automotive Square",
        "sector": "North Arterial Corridor",
        "lat": 21.1873,
        "lng": 79.0984,
        "direction": "Northbound",
        "is_camera": True,
        "status": "ONLINE"
    },
    "CAM-07": {
        "id": "CAM-07",
        "name": "Shankar Nagar Square",
        "sector": "West Sector",
        "lat": 21.1378,
        "lng": 79.0632,
        "direction": "Southwest",
        "is_camera": True,
        "status": "ONLINE"
    },
    "CAM-08": {
        "id": "CAM-08",
        "name": "Law College Square / Amravati Rd",
        "sector": "University Corridor",
        "lat": 21.1462,
        "lng": 79.0543,
        "direction": "Westbound",
        "is_camera": True,
        "status": "ONLINE"
    },
    "CAM-09": {
        "id": "CAM-09",
        "name": "Medical College Square",
        "sector": "Medical Zone",
        "lat": 21.1302,
        "lng": 79.0965,
        "direction": "Southeast",
        "is_camera": True,
        "status": "ONLINE"
    },
    "CAM-10": {
        "id": "CAM-10",
        "name": "Cotton Market Square",
        "sector": "Eastern Market Sector",
        "lat": 21.1425,
        "lng": 79.0912,
        "direction": "Eastbound",
        "is_camera": True,
        "status": "ONLINE"
    },
    "CAM-11": {
        "id": "CAM-11",
        "name": "Mankapur Ring Road Square",
        "sector": "Outer Ring North",
        "lat": 21.1895,
        "lng": 79.0694,
        "direction": "Northbound",
        "is_camera": True,
        "status": "ONLINE"
    },
    "CAM-12": {
        "id": "CAM-12",
        "name": "Rahate Colony Square",
        "sector": "South Central Sector",
        "lat": 21.1278,
        "lng": 79.0768,
        "direction": "Southbound",
        "is_camera": True,
        "status": "ONLINE"
    }
}

# Intermediate Road Junctions & Intersections (Inferred Waypoints)
ROAD_JUNCTIONS = {
    "JCT-01": {
        "id": "JCT-01",
        "name": "Tekdi Ganesh Temple Split",
        "sector": "CBD Radial",
        "lat": 21.1510,
        "lng": 79.0860,
        "direction": "Radial Junction",
        "is_camera": False,
        "status": "UNMONITORED_JUNCTION"
    },
    "JCT-02": {
        "id": "JCT-02",
        "name": "Kasturchand Park Circle",
        "sector": "Central Arts Corridor",
        "lat": 21.1540,
        "lng": 79.0820,
        "direction": "Four-Way Roundabout",
        "is_camera": False,
        "status": "UNMONITORED_JUNCTION"
    },
    "JCT-03": {
        "id": "JCT-03",
        "name": "Baidyanath Chowk",
        "sector": "South-East Arterial",
        "lat": 21.1350,
        "lng": 79.0900,
        "direction": "Arterial Split",
        "is_camera": False,
        "status": "UNMONITORED_JUNCTION"
    },
    "JCT-04": {
        "id": "JCT-04",
        "name": "Dharampeth Shopping Circle",
        "sector": "West Hub",
        "lat": 21.1410,
        "lng": 79.0680,
        "direction": "Roundabout",
        "is_camera": False,
        "status": "UNMONITORED_JUNCTION"
    },
    "JCT-05": {
        "id": "JCT-05",
        "name": "Chatrapati Square Wardha Rd",
        "sector": "South Arterial Corridor",
        "lat": 21.1110,
        "lng": 79.0650,
        "direction": "Expressway Interchange",
        "is_camera": False,
        "status": "UNMONITORED_JUNCTION"
    },
    "JCT-06": {
        "id": "JCT-06",
        "name": "Kadbi Chowk Flyover Split",
        "sector": "Commercial Hub",
        "lat": 21.1730,
        "lng": 79.0900,
        "direction": "Flyover Intersection",
        "is_camera": False,
        "status": "UNMONITORED_JUNCTION"
    },
    "JCT-07": {
        "id": "JCT-07",
        "name": "Indora Square Ring Junction",
        "sector": "North Ring",
        "lat": 21.1760,
        "lng": 79.0960,
        "direction": "Ring Junction",
        "is_camera": False,
        "status": "UNMONITORED_JUNCTION"
    },
    "JCT-08": {
        "id": "JCT-08",
        "name": "Ajni Railway Overbridge",
        "sector": "South Transit Link",
        "lat": 21.1210,
        "lng": 79.0820,
        "direction": "Overbridge Junction",
        "is_camera": False,
        "status": "UNMONITORED_JUNCTION"
    }
}

# Monitored Road Links / Directed Graph Edges
ROAD_EDGES_DATA = [
    # Connaught Place Central Cluster
    {"from": "CAM-01", "to": "CAM-03", "dist_km": 1.3, "time_sec": 140, "dir": "Eastbound", "prob": 0.38, "traffic": "MODERATE"},
    {"from": "CAM-01", "to": "CAM-04", "dist_km": 1.2, "time_sec": 130, "dir": "Southbound", "prob": 0.34, "traffic": "MODERATE"},
    {"from": "CAM-01", "to": "CAM-05", "dist_km": 0.8, "time_sec": 90,  "dir": "Northbound", "prob": 0.28, "traffic": "FREE_FLOW"},

    {"from": "CAM-05", "to": "CAM-01", "dist_km": 0.8, "time_sec": 95,  "dir": "Southbound", "prob": 0.45, "traffic": "FREE_FLOW"},
    {"from": "CAM-05", "to": "JCT-01", "dist_km": 0.9, "time_sec": 110, "dir": "Northbound", "prob": 0.35, "traffic": "MODERATE"},
    {"from": "CAM-05", "to": "CAM-04", "dist_km": 1.4, "time_sec": 160, "dir": "Southbound", "prob": 0.20, "traffic": "MODERATE"},

    {"from": "CAM-03", "to": "JCT-02", "dist_km": 1.1, "time_sec": 120, "dir": "South-East", "prob": 0.52, "traffic": "MODERATE"},
    {"from": "CAM-03", "to": "JCT-08", "dist_km": 2.4, "time_sec": 260, "dir": "Eastbound",  "prob": 0.32, "traffic": "HEAVY"},
    {"from": "CAM-03", "to": "CAM-01", "dist_km": 1.3, "time_sec": 150, "dir": "Westbound",  "prob": 0.16, "traffic": "FREE_FLOW"},

    {"from": "CAM-04", "to": "CAM-02", "dist_km": 1.8, "time_sec": 190, "dir": "South-East", "prob": 0.55, "traffic": "MODERATE"},
    {"from": "CAM-04", "to": "CAM-01", "dist_km": 1.2, "time_sec": 130, "dir": "Northbound", "prob": 0.30, "traffic": "MODERATE"},
    {"from": "CAM-04", "to": "JCT-05", "dist_km": 6.8, "time_sec": 620, "dir": "South-West", "prob": 0.15, "traffic": "HEAVY"},

    # India Gate & South Arterials
    {"from": "CAM-02", "to": "JCT-03", "dist_km": 2.5, "time_sec": 240, "dir": "Southbound", "prob": 0.48, "traffic": "FREE_FLOW"},
    {"from": "CAM-02", "to": "CAM-06", "dist_km": 5.2, "time_sec": 480, "dir": "South-West", "prob": 0.32, "traffic": "MODERATE"},
    {"from": "CAM-02", "to": "CAM-04", "dist_km": 1.8, "time_sec": 200, "dir": "North-West", "prob": 0.20, "traffic": "MODERATE"},

    {"from": "JCT-02", "to": "CAM-02", "dist_km": 1.4, "time_sec": 150, "dir": "Southbound", "prob": 0.65, "traffic": "FREE_FLOW"},
    {"from": "JCT-02", "to": "JCT-08", "dist_km": 1.8, "time_sec": 200, "dir": "North-East", "prob": 0.35, "traffic": "MODERATE"},

    {"from": "JCT-03", "to": "CAM-12", "dist_km": 3.1, "time_sec": 290, "dir": "South-East", "prob": 0.68, "traffic": "MODERATE"},
    {"from": "JCT-03", "to": "CAM-06", "dist_km": 3.8, "time_sec": 360, "dir": "South-West", "prob": 0.32, "traffic": "FREE_FLOW"},

    # Ring Road & Ashram / DND Expressway
    {"from": "CAM-12", "to": "CAM-10", "dist_km": 4.5, "time_sec": 380, "dir": "Eastbound",  "prob": 0.58, "traffic": "FREE_FLOW"},
    {"from": "CAM-12", "to": "CAM-09", "dist_km": 4.9, "time_sec": 440, "dir": "Southbound", "prob": 0.28, "traffic": "HEAVY"},
    {"from": "CAM-12", "to": "JCT-06", "dist_km": 2.8, "time_sec": 260, "dir": "South-West", "prob": 0.14, "traffic": "MODERATE"},

    {"from": "CAM-10", "to": "CAM-12", "dist_km": 4.5, "time_sec": 400, "dir": "Westbound",  "prob": 0.70, "traffic": "MODERATE"},
    {"from": "CAM-10", "to": "JCT-08", "dist_km": 7.8, "time_sec": 650, "dir": "Northbound", "prob": 0.30, "traffic": "FREE_FLOW"},

    {"from": "CAM-09", "to": "CAM-12", "dist_km": 4.9, "time_sec": 450, "dir": "Northbound", "prob": 0.60, "traffic": "HEAVY"},
    {"from": "CAM-09", "to": "JCT-06", "dist_km": 3.2, "time_sec": 310, "dir": "Westbound",  "prob": 0.40, "traffic": "MODERATE"},

    # South Extension & AIIMS Ring Corridor
    {"from": "CAM-06", "to": "JCT-04", "dist_km": 1.2, "time_sec": 120, "dir": "Westbound",  "prob": 0.55, "traffic": "MODERATE"},
    {"from": "CAM-06", "to": "JCT-06", "dist_km": 3.6, "time_sec": 340, "dir": "Eastbound",  "prob": 0.30, "traffic": "FREE_FLOW"},
    {"from": "CAM-06", "to": "CAM-02", "dist_km": 5.2, "time_sec": 500, "dir": "North-East", "prob": 0.15, "traffic": "MODERATE"},

    {"from": "JCT-04", "to": "JCT-05", "dist_km": 5.8, "time_sec": 480, "dir": "North-West", "prob": 0.50, "traffic": "FREE_FLOW"},
    {"from": "JCT-04", "to": "JCT-07", "dist_km": 8.9, "time_sec": 720, "dir": "South-West", "prob": 0.35, "traffic": "MODERATE"},
    {"from": "JCT-04", "to": "CAM-06", "dist_km": 1.2, "time_sec": 130, "dir": "Eastbound",  "prob": 0.15, "traffic": "MODERATE"},

    # Airport & Cyber City Corridor
    {"from": "JCT-05", "to": "CAM-08", "dist_km": 7.2, "time_sec": 520, "dir": "South-West", "prob": 0.62, "traffic": "FREE_FLOW"},
    {"from": "JCT-05", "to": "CAM-04", "dist_km": 6.8, "time_sec": 650, "dir": "North-East", "prob": 0.38, "traffic": "HEAVY"},

    {"from": "JCT-07", "to": "CAM-08", "dist_km": 2.8, "time_sec": 210, "dir": "Westbound",  "prob": 0.70, "traffic": "FREE_FLOW"},
    {"from": "JCT-07", "to": "CAM-07", "dist_km": 6.9, "time_sec": 480, "dir": "South-West", "prob": 0.30, "traffic": "FREE_FLOW"},

    {"from": "CAM-08", "to": "CAM-07", "dist_km": 7.5, "time_sec": 500, "dir": "South-West", "prob": 0.65, "traffic": "FREE_FLOW"},
    {"from": "CAM-08", "to": "JCT-07", "dist_km": 2.8, "time_sec": 220, "dir": "Eastbound",  "prob": 0.35, "traffic": "MODERATE"},

    {"from": "CAM-07", "to": "CAM-08", "dist_km": 7.5, "time_sec": 510, "dir": "North-East", "prob": 0.85, "traffic": "FREE_FLOW"},
    {"from": "CAM-07", "to": "JCT-07", "dist_km": 6.9, "time_sec": 490, "dir": "North-East", "prob": 0.15, "traffic": "FREE_FLOW"},

    # Heritage & North Link
    {"from": "CAM-11", "to": "JCT-01", "dist_km": 1.8, "time_sec": 170, "dir": "South-West", "prob": 0.48, "traffic": "MODERATE"},
    {"from": "CAM-11", "to": "JCT-08", "dist_km": 1.6, "time_sec": 160, "dir": "South-East", "prob": 0.35, "traffic": "MODERATE"},
    {"from": "CAM-11", "to": "CAM-01", "dist_km": 2.5, "time_sec": 240, "dir": "South-West", "prob": 0.17, "traffic": "HEAVY"},

    {"from": "JCT-01", "to": "CAM-01", "dist_km": 1.0, "time_sec": 100, "dir": "Southbound", "prob": 0.60, "traffic": "MODERATE"},
    {"from": "JCT-01", "to": "CAM-11", "dist_km": 1.8, "time_sec": 180, "dir": "Northbound", "prob": 0.40, "traffic": "FREE_FLOW"},

    {"from": "JCT-08", "to": "CAM-11", "dist_km": 1.6, "time_sec": 170, "dir": "North-West", "prob": 0.40, "traffic": "MODERATE"},
    {"from": "JCT-08", "to": "CAM-03", "dist_km": 2.4, "time_sec": 270, "dir": "Westbound",  "prob": 0.35, "traffic": "HEAVY"},
    {"from": "JCT-08", "to": "CAM-10", "dist_km": 7.8, "time_sec": 660, "dir": "South-East", "prob": 0.25, "traffic": "FREE_FLOW"},

    {"from": "JCT-06", "to": "CAM-06", "dist_km": 3.6, "time_sec": 350, "dir": "Westbound",  "prob": 0.45, "traffic": "MODERATE"},
    {"from": "JCT-06", "to": "CAM-12", "dist_km": 2.8, "time_sec": 270, "dir": "North-East", "prob": 0.35, "traffic": "MODERATE"},
    {"from": "JCT-06", "to": "CAM-09", "dist_km": 3.2, "time_sec": 320, "dir": "Eastbound",  "prob": 0.20, "traffic": "HEAVY"}
]

class RoadNetworkGraph:
    """
    Graph representation of the city road and surveillance network.
    Contains camera nodes, intermediate unmonitored road junctions,
    directed road links, dynamic congestion speeds, and observability calculation.
    """

    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.adj_list: Dict[str, List[Dict[str, Any]]] = {}
        self.camera_statuses: Dict[str, str] = {}
        self.build_graph()

    def build_graph(self):
        # Load all camera nodes and road junctions
        for cid, cam in CAMERA_NODES.items():
            self.nodes[cid] = cam.copy()
            self.camera_statuses[cid] = cam.get("status", "ONLINE")

        for jid, jct in ROAD_JUNCTIONS.items():
            self.nodes[jid] = jct.copy()

        # Initialize adjacency list
        for nid in self.nodes:
            self.adj_list[nid] = []

        # Populate directed edges
        for edge in ROAD_EDGES_DATA:
            u, v = edge["from"], edge["to"]
            if u in self.nodes and v in self.nodes:
                self.adj_list[u].append({
                    "to": v,
                    "dist_km": edge["dist_km"],
                    "time_sec": edge["time_sec"],
                    "direction": edge["dir"],
                    "prior_prob": edge["prob"],
                    "traffic": edge["traffic"]
                })

    def set_camera_status(self, camera_id: str, status: str):
        """Updates camera health status: ONLINE, OFFLINE, DEGRADED."""
        if camera_id in self.nodes and self.nodes[camera_id]["is_camera"]:
            self.nodes[camera_id]["status"] = status
            self.camera_statuses[camera_id] = status

    def get_congestion_multiplier(self, traffic_level: str) -> float:
        """Returns travel time multiplier based on traffic level."""
        multipliers = {
            "FREE_FLOW": 1.0,
            "MODERATE": 1.25,
            "HEAVY": 1.65,
            "CONGESTED": 2.20
        }
        return multipliers.get(traffic_level, 1.0)

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self.nodes.get(node_id)

    def is_node_online(self, node_id: str) -> bool:
        """Returns True if node is not offline."""
        node = self.nodes.get(node_id)
        if not node:
            return False
        if not node["is_camera"]:
            return True # Junctions are physical topology
        return node.get("status") != "OFFLINE"

    def get_downstream_camera_predictions(
        self,
        source_cam_id: str,
        current_speed_kmh: float = 45.0,
        max_depth: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Explores outward from source camera node along directed edges.
        Finds reachable downstream cameras, calculates transition probabilities,
        and derives the ETA window taking congestion and offline bypass into account.
        """
        if source_cam_id not in self.nodes:
            return []

        predictions_map: Dict[str, Dict[str, Any]] = {}
        visited_paths: Set[Tuple[str, ...]] = set()

        # Queue items: (current_node, cumulative_prob, cumulative_dist_km, cumulative_time_sec, path_nodes)
        queue = [(source_cam_id, 1.0, 0.0, 0, [source_cam_id])]

        while queue:
            curr_node, curr_prob, curr_dist, curr_time, curr_path = queue.pop(0)

            if len(curr_path) > max_depth + 1:
                continue

            for edge in self.adj_list.get(curr_node, []):
                next_node = edge["to"]
                if next_node in curr_path:
                    continue # Avoid cyclic loops

                edge_prob = edge["prior_prob"]
                cong_mult = self.get_congestion_multiplier(edge["traffic"])
                edge_time = int(edge["time_sec"] * cong_mult)
                edge_dist = edge["dist_km"]

                new_prob = curr_prob * edge_prob
                new_dist = curr_dist + edge_dist
                new_time = curr_time + edge_time
                new_path = curr_path + [next_node]

                path_tuple = tuple(new_path)
                if path_tuple in visited_paths:
                    continue
                visited_paths.add(path_tuple)

                target_node_obj = self.nodes.get(next_node)
                if not target_node_obj:
                    continue

                if target_node_obj["is_camera"]:
                    # If target camera is OFFLINE, we keep propagating through it but do not predict it as observable
                    if target_node_obj.get("status") == "OFFLINE":
                        # Propagate past offline camera
                        queue.append((next_node, new_prob, new_dist, new_time, new_path))
                        continue

                    # Record reachable online camera
                    if next_node not in predictions_map:
                        predictions_map[next_node] = {
                            "camera_id": next_node,
                            "camera_name": target_node_obj["name"],
                            "sector": target_node_obj["sector"],
                            "direction": target_node_obj["direction"],
                            "lat": target_node_obj["lat"],
                            "lng": target_node_obj["lng"],
                            "raw_score": 0.0,
                            "min_time_sec": new_time,
                            "max_time_sec": new_time,
                            "distance_km": round(new_dist, 2),
                            "shortest_path": new_path,
                            "traffic_level": edge["traffic"]
                        }

                    pred = predictions_map[next_node]
                    pred["raw_score"] += new_prob
                    pred["min_time_sec"] = min(pred["min_time_sec"], int(new_time * 0.85))
                    pred["max_time_sec"] = max(pred["max_time_sec"], int(new_time * 1.35))
                    if new_dist < pred["distance_km"]:
                        pred["distance_km"] = round(new_dist, 2)
                        pred["shortest_path"] = new_path

                    # Continue propagating beyond 1st hop up to max_depth
                    if len(new_path) <= max_depth:
                        queue.append((next_node, new_prob * 0.75, new_dist, new_time, new_path))
                else:
                    # Intermediate unmonitored junction: propagate through
                    queue.append((next_node, new_prob, new_dist, new_time, new_path))

        # Normalize probabilities across predicted downstream cameras
        total_raw = sum(p["raw_score"] for p in predictions_map.values()) or 1.0
        results = []

        for cid, pred in predictions_map.items():
            prob = min(0.96, max(0.04, round(pred["raw_score"] / total_raw, 3)))
            eta_min_m = max(1, math.ceil(pred["min_time_sec"] / 60.0))
            eta_max_m = max(eta_min_m + 1, math.ceil(pred["max_time_sec"] / 60.0))

            results.append({
                "camera_id": cid,
                "camera_name": pred["camera_name"],
                "sector": pred["sector"],
                "lat": pred["lat"],
                "lng": pred["lng"],
                "probability": prob,
                "percentage": int(prob * 100),
                "eta_text": f"{eta_min_m}-{eta_max_m} mins",
                "eta_min_seconds": pred["min_time_sec"],
                "eta_max_seconds": pred["max_time_sec"],
                "distance_km": pred["distance_km"],
                "path_nodes": pred["shortest_path"],
                "factors": {
                    "directional_alignment": 0.88 if pred["direction"] != "Unknown" else 0.70,
                    "historical_transition": round(min(0.95, prob * 1.1), 2),
                    "road_connectivity": "Direct / Shortest Arterial",
                    "congestion_factor": pred["traffic_level"]
                }
            })

        results.sort(key=lambda x: x["probability"], reverse=True)
        return results

    def generate_route_hypotheses(
        self,
        source_cam_id: str,
        max_routes: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generates probable multi-step route hypotheses departing source camera.
        Explicitly distinguishes between OBSERVED nodes, INFERRED junctions, and PREDICTED endpoints.
        """
        if source_cam_id not in self.nodes:
            return []

        hypotheses = []
        raw_preds = self.get_downstream_camera_predictions(source_cam_id)

        for i, pred in enumerate(raw_preds[:max_routes]):
            path_nodes = pred["path_nodes"]
            path_steps = []

            for step_idx, nid in enumerate(path_nodes):
                node_obj = self.nodes.get(nid, {})
                if step_idx == 0:
                    status_type = "OBSERVED"
                elif step_idx == len(path_nodes) - 1:
                    status_type = "PREDICTED"
                else:
                    status_type = "INFERRED" if not node_obj.get("is_camera") else "OBSERVED_CORRIDOR"

                path_steps.append({
                    "node_id": nid,
                    "name": node_obj.get("name", nid),
                    "sector": node_obj.get("sector", ""),
                    "lat": node_obj.get("lat", 0.0),
                    "lng": node_obj.get("lng", 0.0),
                    "is_camera": node_obj.get("is_camera", False),
                    "status_type": status_type,
                    "status": node_obj.get("status", "ONLINE")
                })

            hypotheses.append({
                "hypothesis_id": f"HYP-{source_cam_id}-{pred['camera_id']}-{i+1}",
                "target_camera_id": pred["camera_id"],
                "target_camera_name": pred["camera_name"],
                "probability": pred["probability"],
                "percentage": pred["percentage"],
                "eta_text": pred["eta_text"],
                "distance_km": pred["distance_km"],
                "steps": path_steps,
                "summary": f"{source_cam_id} → {pred['camera_id']} ({pred['percentage']}%)"
            })

        return hypotheses

    def calculate_network_observability(self) -> Dict[str, Any]:
        """
        Computes overall network visibility and identifies coverage blind spots
        when cameras are offline or degraded.
        """
        total_cams = len(CAMERA_NODES)
        online_cams = sum(1 for c in CAMERA_NODES if self.camera_statuses.get(c) == "ONLINE")
        degraded_cams = sum(1 for c in CAMERA_NODES if self.camera_statuses.get(c) == "DEGRADED")
        offline_cams = sum(1 for c in CAMERA_NODES if self.camera_statuses.get(c) == "OFFLINE")

        # Baseline weighted observability
        observability_pct = round(((online_cams * 1.0 + degraded_cams * 0.5) / total_cams) * 94.0, 1)

        # Identify blind spot corridors
        blind_spots = []
        for cid, status in self.camera_statuses.items():
            if status in ["OFFLINE", "DEGRADED"]:
                cam = CAMERA_NODES[cid]
                # Find adjacent junctions
                adj_links = [e["to"] for e in self.adj_list.get(cid, [])]
                blind_spots.append({
                    "camera_id": cid,
                    "camera_name": cam["name"],
                    "sector": cam["sector"],
                    "status": status,
                    "impact": f"Coverage dropped around {cam['sector']} corridor ({', '.join(adj_links[:2])})",
                    "severity": "CRITICAL" if status == "OFFLINE" else "WARNING"
                })

        return {
            "total_cameras": total_cams,
            "online_cameras": online_cams,
            "degraded_cameras": degraded_cams,
            "offline_cameras": offline_cams,
            "observability_percentage": observability_pct,
            "baseline_percentage": 94.0,
            "status_label": "OPTIMAL_GRID" if observability_pct >= 90 else "DEGRADED_VISIBILITY" if observability_pct >= 70 else "CRITICAL_BLIND_SPOTS",
            "blind_spots": blind_spots
        }

    def get_topology_geojson(self) -> Dict[str, Any]:
        """Exports nodes and road links for GIS map rendering."""
        node_features = []
        for nid, n in self.nodes.items():
            node_features.append({
                "id": nid,
                "name": n["name"],
                "sector": n["sector"],
                "lat": n["lat"],
                "lng": n["lng"],
                "is_camera": n["is_camera"],
                "status": n.get("status", "ONLINE"),
                "direction": n.get("direction", "")
            })

        edges = []
        for edge in ROAD_EDGES_DATA:
            u, v = edge["from"], edge["to"]
            n1, n2 = self.nodes.get(u), self.nodes.get(v)
            if n1 and n2:
                edges.append({
                    "from": u,
                    "to": v,
                    "coords": [[n1["lat"], n1["lng"]], [n2["lat"], n2["lng"]]],
                    "dist_km": edge["dist_km"],
                    "time_sec": edge["time_sec"],
                    "direction": edge["dir"],
                    "traffic": edge["traffic"],
                    "prob": edge["prob"]
                })

        return {
            "nodes": node_features,
            "edges": edges,
            "observability": self.calculate_network_observability()
        }

road_graph = RoadNetworkGraph()
