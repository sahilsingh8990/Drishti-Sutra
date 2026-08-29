# 🚗 Drishti-Sutra (दृष्टि सूत्र) - Real-Time ANPR System

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![YOLO](https://img.shields.io/badge/YOLO-Ultralytics-green.svg)](https://github.com/ultralytics/ultralytics)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-red.svg)](https://opencv.org/)
[![EasyOCR](https://img.shields.io/badge/OCR-EasyOCR-yellow.svg)](https://github.com/JaidedAI/EasyOCR)

**Drishti-Sutra** is an intelligent, high-performance Automatic Number Plate Recognition (ANPR) and vehicle logging system designed for real-time video feeds, multi-camera surveillance, and traffic management.

---

## ✨ Features

- **High-Accuracy Plate Detection**: Utilizes a custom fine-tuned YOLO model (`plate_model.pt`) optimized for vehicle license plates under various lighting conditions and angles.
- **Multi-Engine OCR Support**:
  - **Offline / Local OCR**: Integrated with [EasyOCR](https://github.com/JaidedAI/EasyOCR) for standalone edge deployments.
  - **Cloud Workflow OCR**: Integrated with [Roboflow Inference](https://roboflow.com/) for high-throughput cloud inference pipelines.
- **Temporal Plate Confirmation**: Multi-frame temporal voting ensures only persistent and verified plates are logged, reducing OCR hallucinations.
- **Intelligent Deduplication**: Customizable cooldown timer prevents duplicate entries of the same vehicle during continuous tracking.
- **Indian & Global Plate Validation**: Built-in regex filters for standard Indian registration format (`XX 00 XX 0000`) with support for configurable international formats.
- **Automated Logging & Snapshots**:
  - Automatically appends detection logs to an Excel spreadsheet (`vehicle_data.xlsx`).
  - Saves high-resolution cropped snapshots of verified plates to disk.
- **Multi-Camera & RTSP Streaming**: Ready for multi-source CCTV / IP camera surveillance feeds.
- **End-to-End Training Pipeline**: Includes tools to convert Pascal VOC XML annotations to YOLO format, split datasets, and train custom YOLO detection models.

---

## 📁 Repository Structure

```text
Drishti-Sutra/
│
├── config.py                  # Central configuration (thresholds, paths, camera settings)
├── main.py                    # Production-grade ANPR pipeline with temporal tracking & UI
├── local_live_anpr.py         # Lightweight local live webcam ANPR script
├── live_multi_camera.py       # Multi-camera / RTSP stream ANPR with Roboflow
│
├── test_local_model.py        # Test script for local YOLO plate detector
├── test_roboflow.py           # Test script for Roboflow API integration
├── video_test.py              # Test script for video file inference
│
├── plate_model.pt             # Trained YOLO license plate detection weights
├── yolo11n.pt                 # YOLO base model
├── data.yaml                  # YOLO dataset configuration
│
├── training/                  # Custom model training utilities
│   ├── convert_xml_to_yolo.py # XML (Pascal VOC) to YOLO txt format converter
│   ├── split_dataset.py       # Train / Validation dataset splitter
│   └── train_plate_model.py   # YOLO model fine-tuning script
│
├── requirements.txt           # Python dependencies
└── .gitignore                 # Files ignored from Git tracking
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.8 to 3.12 installed
- Git installed
- Webcam or RTSP IP camera feed

### 2. Clone the Repository
```bash
git clone https://github.com/sahilsingh8990/Drishti-Sutra.git
cd Drishti-Sutra
```

### 3. Create a Virtual Environment & Install Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

---

## 💻 Usage

### 1. Run Main Live ANPR Pipeline
Run the full-featured live system with real-time HUD overlays, temporal tracking, snapshot capture, and automatic Excel logging:
```bash
python main.py
```
- Press `q` to safely exit.

### 2. Run Single Camera Live Detection
```bash
python local_live_anpr.py
```

### 3. Run Multi-Camera / Roboflow Stream
Set your Roboflow API key and launch multi-camera monitoring:
```bash
# Set API Key in terminal
# Windows (CMD): set ROBOFLOW_API_KEY=your_key_here
# Windows (PowerShell): $env:ROBOFLOW_API_KEY="your_key_here"
# Linux/macOS: export ROBOFLOW_API_KEY="your_key_here"

python live_multi_camera.py
```

---

## ⚙️ Configuration

All major parameters can be tweaked inside `config.py`:
- `CAMERA_SOURCE`: Set to `0` for default webcam, or an RTSP stream URL (`"rtsp://..."`).
- `PLATE_DETECTION_CONFIDENCE`: YOLO plate detection threshold (default: `0.40`).
- `OCR_MIN_CONFIDENCE`: Minimum acceptable OCR confidence score (default: `0.35`).
- `MIN_CONFIRMATIONS`: Number of consecutive frames needed before logging a plate (default: `3`).
- `DUPLICATE_COOLDOWN`: Cooldown window in seconds before logging the same plate again (default: `30`).
- `INDIAN_PLATES_ONLY`: Boolean toggle for strict Indian license plate regex matching.

---

## 🛠️ Model Training

To train the detector on your own dataset:
1. Place XML annotations in `annotations/` and images in `images/`.
2. Convert XML annotations to YOLO format:
   ```bash
   python training/convert_xml_to_yolo.py
   ```
3. Split the dataset into train/validation sets:
   ```bash
   python training/split_dataset.py
   ```
4. Start YOLO fine-tuning:
   ```bash
   python training/train_plate_model.py
   ```

---

## 📄 License
This project is licensed under the MIT License.
