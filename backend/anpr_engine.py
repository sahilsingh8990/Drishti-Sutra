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

    def preprocess_plate(self, plate_img: np.ndarray) -> np.ndarray:
        if plate_img is None or plate_img.size == 0:
            return plate_img
        h, w = plate_img.shape[:2]
        if w < 240:
            scale = 240 / max(w, 1)
            plate_img = cv2.resize(plate_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(gray)

    def run_ocr(self, plate_crop: np.ndarray) -> Tuple[str, float]:
        if plate_crop is None or plate_crop.size == 0 or not self.reader:
            return "", 0.0
        try:
            processed = self.preprocess_plate(plate_crop)
            results = self.reader.readtext(processed, detail=1, paragraph=False)
            if not results:
                return "", 0.0

            best_text = ""
            best_conf = 0.0
            full_texts = []
            for bbox, text, conf in results:
                cleaned = self.clean_plate(text)
                if len(cleaned) >= 3:
                    full_texts.append(cleaned)
                    if conf > best_conf:
                        best_conf = float(conf)

            combined = "".join(full_texts)
            corrected = self.correct_plate_ocr(combined)
            return corrected, best_conf
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
                    is_valid = self.validate_indian_plate(plate_text)
                    detections.append({
                        "plate_number": plate_text,
                        "detection_conf": round(det_conf, 2),
                        "ocr_conf": round(ocr_conf, 2),
                        "bbox": [x1, y1, x2, y2],
                        "camera_id": camera_id,
                        "is_valid": is_valid
                    })

                    # Draw high-tech bounding box & HUD label
                    color = (0, 255, 128) if is_valid else (0, 215, 255)
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    
                    label = f"{plate_text} ({int(ocr_conf*100)}%)"
                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(annotated_frame, (x1, y1 - 22), (x1 + tw + 10, y1), color, -1)
                    cv2.putText(annotated_frame, label, (x1 + 5, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
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
