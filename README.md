# 🏙️ City-Wide AI Engine for Multi-Camera ANPR Trajectory Tracking and Urban Traffic Analytics

[![Platform](https://img.shields.io/badge/Platform-Drishti--Sutra-0A84FF.svg)](https://github.com/sahilsingh8990/Drishti-Sutra)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![YOLO](https://img.shields.io/badge/YOLO-Ultralytics%20v11-green.svg)](https://github.com/ultralytics/ultralytics)
[![FastAPI](https://img.shields.io/badge/FastAPI-High%20Performance-teal.svg)](https://fastapi.tiangolo.com/)
[![Leaflet](https://img.shields.io/badge/GIS-Leaflet.js%20%2B%20OSM-brightgreen.svg)](https://leafletjs.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-red.svg)](https://opencv.org/)

A centralized, enterprise-grade AI software platform that processes multi-camera feeds across a city-wide Automatic Number Plate Recognition (ANPR) camera network. The platform links camera data across space and time to provide:
1. **High-Accuracy ANPR & OCR Engine** (>90% accuracy across real-world multi-lane conditions).
2. **Single Plate Spatio-Temporal Trajectory Tracking** (Full historical route reconstruction & anomaly detection on GIS maps).
3. **Macro Urban Traffic Flow & Movement Analytics** (Real-time GIS density heatmaps, Origin-Destination matrices, and congestion bottleneck detection).
4. **Real-Time Security Alert & Blacklist Monitoring** (Instant notification of stolen/flagged vehicles and cloned plate anomalies).

---

## 🌟 Core System Pillars

### 1. 🎯 High-Accuracy ANPR & OCR Engine
- **Custom-Trained YOLO Plate Detector (`plate_model.pt`)**: Detects license plates across difficult angles, poor lighting, and multi-lane traffic streams.
- **Dual-Mode OCR Engine**:
  - **Local Offline Engine**: EasyOCR with temporal voting and confidence thresholding.
  - **Cloud Inference**: Roboflow Serverless API for scalable cloud deployments.
- **Temporal Plate Confirmation**: Multi-frame consensus voting eliminates OCR hallucinations.
- **Indian & Global Registration Validation**: Strict regex filtering for Indian standard formats (`XX 00 XX 0000`) with configurable international support.

### 2. 🗺️ Spatio-Temporal Trajectory Reconstruction
- **Chronological Path Reconstruction**: Queries any vehicle license plate to reconstruct its complete travel trajectory across all geographically distributed city cameras.
- **Inter-Node Kinematics**: Computes geodetic transit distance, transit duration, average speed ($v = \Delta d / \Delta t$), and direction vectors.
- **Trajectory Anomaly Detection**:
  - **Cloned Plate / Teleportation Alert**: Detects physically impossible speeds (>140 km/h) between camera nodes.
  - **Suspicious Looping**: Flags vehicles repeatedly circling high-security perimeters.

### 3. 📊 Macro Urban Traffic Analytics & GIS Heatmaps
- **GIS Traffic Density Heatmaps**: Real-time Leaflet.heat map visualization of vehicle density across sectors.
- **Origin-Destination (OD) Flow Matrix**: Macro mobility matrix mapping trip volumes between city zones.
- **Congestion & Bottleneck Radar**: Automatic detection of choke points based on queue accumulation and throughput drops.
- **Hourly Volume Dynamics**: 24-hour traffic volume curves, peak vs. off-peak analytics, and vehicle class distributions.

### 4. 🚨 Real-Time Security Alert & Blacklist System
- **Watchlist / Blacklist Management**: Track vehicles categorized as Stolen, Wanted, Suspicious, Violators, or Expired Documents.
- **Instant Audio-Visual Alerts**: Live WebSocket alerts triggered upon camera detection with vehicle snapshot, timestamp, and location.
- **Exportable Investigation Dossiers**: One-click printable PDF/HTML investigation reports.

---

## 📁 Repository Structure

```text
├── backend/
│   ├── app.py                  # FastAPI server, REST API endpoints, WebSocket hub
│   ├── database.py             # SQLite database ORM: Cameras, Detections, Blacklist, Alerts
│   ├── trajectory_engine.py    # Spatio-temporal route reconstruction & anomaly detection
│   ├── analytics_engine.py     # Density heatmaps, OD matrix, congestion bottlenecks, trends
│   ├── camera_manager.py       # Multi-camera registry, live feed processor & simulator
│   └── seed_data.py            # Rich city simulation data (12+ camera nodes, realistic routes)
│
├── frontend/
│   ├── index.html              # Command Center UI (Dark Cyberpunk / Traffic Ops)
│   ├── css/style.css           # Custom styles, animations, radar pulses, timeline styling
│   └── js/
│       ├── app.js              # State manager, WebSocket listener, tab routing
│       ├── map_controller.js   # Leaflet GIS map, trajectory polylines, heatmaps, camera pins
│       ├── analytics_charts.js # Chart.js integrations (OD matrix, peak volume, congestion)
│       └── alerts_manager.js   # Real-time alert toasts, audio chimes, blacklist modal
│
├── config.py                   # Centralized configuration & camera registry
├── main.py                     # Live ANPR engine hooked into backend DB & WebSocket events
├── local_live_anpr.py          # Standalone live single-camera script
├── run_dashboard.py            # One-click startup script for the entire platform
├── plate_model.pt              # Trained YOLO license plate detection weights
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

---

## 🚀 Quick Start Guide

### 1. Installation
```bash
# Clone repository
git clone https://github.com/sahilsingh8990/Drishti-Sutra.git
cd Drishti-Sutra

# Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Launch the Central Command Center Dashboard
```bash
python run_dashboard.py
```
This automatically initializes the database, seeds the 12+ city camera network with realistic sample traffic, and opens the Command Center at **`http://localhost:8000`**.

### 3. Run Live Camera Detection
To stream live webcam/CCTV feed directly into the city network:
```bash
python main.py
```
Detections will automatically record to the database and trigger live WebSocket alerts on the dashboard!

---

## 📜 License
This project is licensed under the MIT License.
