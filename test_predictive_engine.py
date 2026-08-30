import sys
import os
from pathlib import Path

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.identity_engine import identity_engine
from backend.road_graph import road_graph
from backend.predictive_handoff_engine import predictive_engine
from backend.database import init_db
from backend.seed_data import seed_database

def test_identity_engine():
    print("\n--- 1. Testing Confidence-Aware Identity Engine ---")
    # Test OCR confusion resolution
    raw1 = "258H25340" # 8 instead of B, 0 instead of O
    norm1 = identity_engine.normalize_plate(raw1)
    print(f"Raw OCR: {raw1} -> Normalized: {norm1}")
    assert norm1 == "25BH2534O", f"Expected 25BH2534O but got {norm1}"

    # Test candidate variants distribution
    variants = identity_engine.generate_candidate_variants(raw1, ocr_conf=0.88)
    print("Generated candidate variants:")
    for v in variants:
        print(f"  - {v['plate']}: {v['percentage']}% (Valid: {v['is_valid_structure']})")
    assert any(v["plate"] == "25BH2534O" for v in variants)

    # Test multi-camera observation Bayesian update
    obs1 = identity_engine.resolve_or_update_identity("258H25340", "CAM-01", 0.92, 0.85)
    print(f"Observation 1 (CAM-01): Resolved: {obs1['resolved_plate']}, Conf: {obs1['identity_confidence']}")

    obs2 = identity_engine.resolve_or_update_identity("25BH25340", "CAM-04", 0.95, 0.90)
    print(f"Observation 2 (CAM-04): Resolved: {obs2['resolved_plate']}, Conf: {obs2['identity_confidence']}")

    obs3 = identity_engine.resolve_or_update_identity("25BH2534O", "CAM-02", 0.98, 0.95)
    print(f"Observation 3 (CAM-02): Resolved: {obs3['resolved_plate']}, Conf: {obs3['identity_confidence']}")

    assert obs3["identity_confidence"] >= obs1["identity_confidence"]
    print("✓ Identity engine tests passed!")

def test_road_graph_and_blind_spots():
    print("\n--- 2. Testing Road Network Graph & Observability ---")
    # Normal observability
    road_graph.set_camera_status("CAM-04", "ONLINE")
    obs_normal = road_graph.calculate_network_observability()
    print(f"Normal Observability: {obs_normal['observability_percentage']}% | Status: {obs_normal['status_label']}")
    assert obs_normal["observability_percentage"] >= 90.0

    # Predictions departing CAM-01
    preds = road_graph.get_downstream_camera_predictions("CAM-01")
    print("Downstream predictions departing CAM-01 (All Online):")
    for p in preds[:3]:
        print(f"  - {p['camera_id']} ({p['camera_name']}): {p['percentage']}% | ETA: {p['eta_text']} | Dist: {p['distance_km']}km")
    assert len(preds) > 0

    # Simulate CAM-04 OFFLINE (Blind spot test)
    road_graph.set_camera_status("CAM-04", "OFFLINE")
    obs_degraded = road_graph.calculate_network_observability()
    print(f"CAM-04 OFFLINE Observability: {obs_degraded['observability_percentage']}% | Blind spots: {len(obs_degraded['blind_spots'])}")
    assert obs_degraded["observability_percentage"] < obs_normal["observability_percentage"]
    assert len(obs_degraded["blind_spots"]) > 0

    # Verify rerouting: CAM-04 should NOT be predicted as observable endpoint
    preds_offline = road_graph.get_downstream_camera_predictions("CAM-01")
    assert all(p["camera_id"] != "CAM-04" for p in preds_offline), "CAM-04 should be excluded from observable predictions"
    print("✓ Dynamic blind spot handling & route rerouting passed!")

    # Reset
    road_graph.set_camera_status("CAM-04", "ONLINE")

def test_predictive_handoff_and_reacquisition():
    print("\n--- 3. Testing Predictive Handoff Engine & Reacquisition ---")
    pred_res = predictive_engine.predict_next_cameras(
        plate_number="MH49AE2355",
        current_camera_id="CAM-01",
        detection_conf=0.96,
        ocr_conf=0.94,
        vehicle_type="Sedan (White)",
        is_blacklisted=True
    )
    print(f"Target: {pred_res['resolved_plate']} | Predictions: {len(pred_res['predictions'])}")
    for p in pred_res["predictions"][:2]:
        print(f"  - {p['camera_id']}: {p['percentage']}% | Factors: {len(p['explainability_factors'])}")

    # Dispatch handoff watch queue
    created_handoffs = predictive_engine.dispatch_active_handoffs(
        plate_number=pred_res["resolved_plate"],
        current_camera_id="CAM-01",
        predictions=pred_res["predictions"],
        is_blacklisted=True
    )
    print(f"Dispatched {len(created_handoffs)} priority handoff watch requests.")
    assert len(created_handoffs) > 0

    # Reacquire at target camera
    target_cam = created_handoffs[0]["target_camera_id"]
    reacq = predictive_engine.evaluate_reacquisition(
        incoming_plate="MH49AE2355",
        incoming_camera_id=target_cam,
        incoming_conf=0.95
    )
    print(f"Reacquisition Result: was_correct={reacq['was_correct']}, accuracy={reacq['eta_accuracy_label']}, ETA error={reacq['eta_error_sec']}s")
    assert reacq is not None
    assert reacq["was_correct"] is True

    stats = predictive_engine.get_reacquisition_statistics()
    print(f"Reacquisition Accuracy: {stats['accuracy_percentage']}% ({stats['correct_predictions']}/{stats['total_evaluations']})")
    print("✓ Predictive handoff & reacquisition tests passed!")

def test_api_endpoints():
    print("\n--- 4. Testing FastAPI Application Endpoints ---")
    from fastapi.testclient import TestClient
    from backend.app import app

    client = TestClient(app)

    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200

    # 2. Predictive active tracks
    res = client.get("/api/predictive/active-tracks")
    assert res.status_code == 200
    print(f"Active tracks endpoint returned {len(res.json())} tracks.")

    # 3. Track detailed endpoint for 25BH2534O
    res = client.get("/api/predictive/track/25BH2534O")
    assert res.status_code == 200
    track_data = res.json()
    print(f"Track dossier: Plate={track_data['plate_number']}, Conf={track_data['identity_confidence']}, Candidates={len(track_data['candidate_identities'])}, Predictions={len(track_data['next_camera_predictions'])}")
    assert len(track_data["candidate_identities"]) > 0

    # 4. Handoffs endpoint
    res = client.get("/api/predictive/handoffs")
    assert res.status_code == 200

    # 5. Network observability endpoint
    res = client.get("/api/predictive/network-observability")
    assert res.status_code == 200
    print(f"Network Observability API: {res.json()['observability_percentage']}%")

    # 6. Camera status toggle endpoint
    res = client.post("/api/cameras/CAM-04/status", json={"status": "OFFLINE"})
    assert res.status_code == 200
    assert res.json()["status"] == "OFFLINE"

    # Restore to ONLINE
    client.post("/api/cameras/CAM-04/status", json={"status": "ONLINE"})

    print("✓ All FastAPI endpoints passed successfully!")

if __name__ == "__main__":
    init_db()
    seed_database(force=False)
    test_identity_engine()
    test_road_graph_and_blind_spots()
    test_predictive_handoff_and_reacquisition()
    test_api_endpoints()
    print("\n==========================================")
    print(">> ALL PREDICTIVE ENGINE TESTS PASSED!")
    print("==========================================\n")
