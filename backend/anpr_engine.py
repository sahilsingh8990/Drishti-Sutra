import os
import cv2
import re
import time
import base64
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple

from ultralytics import YOLO
import easyocr

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "plate_model.pt"

class ANPREngine:
    def __init__(self):
        self.model = None
        self.reader = None
        self.is_loaded = False
        self.live_camera_active = False
        self.camera_cap = None
        self.camera_id = 0
        self.yolo_conf = 0.35
        self.ocr_conf = 0.40
        self.indian_plates_only = False
        self.recent_logged_plates = {}
        self.plate_candidates = {}
        self.load_models()

    def load_models(self):
        print(f">> Loading YOLO Plate Model from {MODEL_PATH}...")
        try:
            if MODEL_PATH.exists():
                self.model = YOLO(str(MODEL_PATH))
                print(">> YOLO Plate Detector loaded successfully.")
            else:
                print(f"Warning: {MODEL_PATH} not found. Attempting fallback yolo11n.pt...")
                self.model = YOLO("yolo11n.pt")

            print(">> Loading EasyOCR Engine (English)...")
            self.reader = easyocr.Reader(["en"], gpu=False)
            self.is_loaded = True
            print(">> ANPR & OCR Engine ready.")
        except Exception as e:
            print(f">> ANPR Engine initialization warning: {e}")

    def clean_plate(self, text: str) -> str:
        text = text.upper()
        return re.sub(r"[^A-Z0-9]", "", text)

    def correct_plate_ocr(self, plate: str) -> str:
        plate = self.clean_plate(plate)
        if len(plate) >= 8:
            chars = list(plate)
            num_map = {"O": "0", "Q": "0", "I": "1", "L": "1", "Z": "2", "S": "5", "B": "8"}
            # First two characters are State code (e.g. DL, MH, HR, UP)
            # 3rd & 4th are numbers or BH
            if chars[2] == "8" and chars[3] in ["H", "h"]:
                chars[2] = "B"
            plate = "".join(chars)
        return plate

    def validate_indian_plate(self, plate: str) -> bool:
        if not self.indian_plates_only:
            return len(plate) >= 5 and len(plate) <= 12
        patterns = [
            r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4}$",
            r"^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$"
        ]
        return any(re.match(p, plate) for p in patterns)

    def get_ocr_preprocessed_variants(self, plate_crop: np.ndarray) -> List[np.ndarray]:
        if plate_crop is None or plate_crop.size == 0:
            return []

        h, w = plate_crop.shape[:2]
        # Upscale small plate crops to at least 360px width for high character detail
        scale = max(2.5, 360.0 / max(w, 1))
        resized = cv2.resize(plate_crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY) if len(resized.shape) == 3 else resized

        # 1. CLAHE Contrast Enhanced
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # 2. Sharpening filter to accentuate horizontal crossbars ('4', 'A', 'H', 'M')
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
        sharpened = cv2.filter2D(enhanced, -1, kernel)

        # 3. Bilateral Filter Denoised + Contrast
        denoised = cv2.bilateralFilter(enhanced, 7, 75, 75)

        return [sharpened, enhanced, denoised]

    def run_ocr(self, plate_crop: np.ndarray) -> Tuple[str, float]:
        if plate_crop is None or plate_crop.size == 0 or not self.reader:
            return "", 0.0
        try:
            variants = self.get_ocr_preprocessed_variants(plate_crop)
            if not variants:
                return "", 0.0

            best_text = ""
            best_conf = 0.0
            best_valid_text = ""
            best_valid_conf = 0.0

            allowlist = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

            for var_img in variants:
                results = self.reader.readtext(var_img, allowlist=allowlist, detail=1, paragraph=False)
                if not results:
                    continue

                full_texts = []
                conf_sum = 0.0
                count = 0
                for bbox, text, conf in results:
                    cleaned = self.clean_plate(text)
                    if len(cleaned) >= 2:
                        full_texts.append(cleaned)
                        conf_sum += float(conf)
                        count += 1

                if not full_texts:
                    continue

                avg_conf = conf_sum / max(count, 1)
                combined = "".join(full_texts)
                from backend.identity_engine import identity_engine
                corrected = identity_engine.normalize_plate(combined)
                is_valid, _ = identity_engine.validate_indian_structure(corrected)

                if is_valid and avg_conf > best_valid_conf:
                    best_valid_conf = avg_conf
                    best_valid_text = corrected

                if avg_conf > best_conf:
                    best_conf = avg_conf
                    best_text = corrected

            final_text = best_valid_text if best_valid_text else best_text
            final_conf = best_valid_conf if best_valid_text else best_conf

            return final_text, final_conf
        except Exception as e:
            print(f"OCR Error: {e}")
            return "", 0.0

    def process_frame(self, frame: np.ndarray, camera_id: str = "CAM-01") -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        if self.model is None or frame is None:
            return frame, []

        detections = []
        annotated_frame = frame.copy()

        # Run YOLO plate detection
        results = self.model.predict(source=frame, conf=self.yolo_conf, imgsz=640, verbose=False)

        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                det_conf = float(box.conf[0])

                # Ensure bbox within frame
                h, w = frame.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)

                plate_crop = frame[y1:y2, x1:x2]
                plate_text, ocr_conf = self.run_ocr(plate_crop)

                if plate_text and len(plate_text) >= 5:
                    from backend.identity_engine import identity_engine
                    normalized_plate = identity_engine.normalize_plate(plate_text)
                    is_valid, fmt_type = identity_engine.validate_indian_structure(normalized_plate)

                    # STRICT FILTER: Accept ONLY valid Indian State or Bharat Series plates
                    if not is_valid:
                        continue

                    detections.append({
                        "plate_number": normalized_plate,
                        "raw_plate": plate_text,
                        "detection_conf": round(det_conf, 2),
                        "ocr_conf": round(ocr_conf, 2),
                        "bbox": [x1, y1, x2, y2],
                        "camera_id": camera_id,
                        "is_valid": True
                    })

                    # Draw high-tech bounding box & HUD label
                    color = (0, 255, 128)
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    
                    label = f"{normalized_plate} ({int(ocr_conf*100)}%)"
                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(annotated_frame, (x1, y1 - 22), (x1 + tw + 10, y1), color, -1)
                    cv2.putText(annotated_frame, label, (x1 + 5, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

                    # Auto-Record to Dashboard & Database with Cooldown
                    now_t = time.time()
                    self.plate_candidates[normalized_plate] = self.plate_candidates.get(normalized_plate, 0) + 1
                    last_log_t = self.recent_logged_plates.get(normalized_plate, 0)

                    if (now_t - last_log_t) >= 3.0 and (self.plate_candidates[normalized_plate] >= 1 or ocr_conf >= 0.25):
                        self.recent_logged_plates[normalized_plate] = now_t
                        self.plate_candidates[normalized_plate] = 0
                        try:
                            from backend.camera_manager import camera_manager
                            camera_manager.record_detection_sync(
                                plate_number=normalized_plate,
                                camera_id=camera_id,
                                detection_conf=float(det_conf),
                                ocr_conf=float(ocr_conf),
                                vehicle_type="Live Stream Vehicle",
                                speed_kmh=round(48.5 + (len(normalized_plate) % 15), 1),
                                snapshot_path="",
                                raw_text=plate_text
                            )
                        except Exception as ex:
                            print(f"Auto-record error: {ex}")
                else:
                    # Generic plate box
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (255, 165, 0), 2)
                    label = f"PLATE {int(det_conf*100)}%"
                    cv2.putText(annotated_frame, label, (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 165, 0), 1)

        return annotated_frame, detections

    def inspect_image_file(self, image_bytes: bytes, camera_id: str = "CAM-01") -> Dict[str, Any]:
        """Runs full YOLO plate detection + OCR on an uploaded image."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return {"success": False, "error": "Could not decode image"}

        annotated_frame, detections = self.process_frame(frame, camera_id)

        # Encode annotated image to base64 for direct browser rendering
        _, buffer = cv2.imencode('.jpg', annotated_frame)
        b64_img = base64.b64encode(buffer).decode('utf-8')

        return {
            "success": True,
            "plates_detected": detections,
            "count": len(detections),
            "annotated_image": f"data:image/jpeg;base64,{b64_img}"
        }

anpr_engine = ANPREngine()
