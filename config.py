from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "plate_model.pt"

OUTPUT_DIR = BASE_DIR / "output"
SNAPSHOT_DIR = OUTPUT_DIR / "snapshots"

EXCEL_FILE = OUTPUT_DIR / "vehicle_data.xlsx"


# ============================================================
# CAMERA
# ============================================================

# 0 = default laptop/USB camera
CAMERA_SOURCE = 0

CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720


# ============================================================
# YOLO LICENSE PLATE DETECTION
# ============================================================

PLATE_DETECTION_CONFIDENCE = 0.40

# Larger image sizes generally help with small plates,
# but require more processing power.
YOLO_IMAGE_SIZE = 960


# ============================================================
# OCR
# ============================================================

OCR_MIN_CONFIDENCE = 0.35

# Minimum / maximum accepted plate text length
MIN_PLATE_LENGTH = 6
MAX_PLATE_LENGTH = 12


# ============================================================
# TEMPORAL CONFIRMATION
# ============================================================

# Plate must be recognized this many times before saving.
# Reduces false OCR results considerably.
MIN_CONFIRMATIONS = 3

# Recognition observations expire after this many seconds.
TRACK_TIMEOUT = 3.0


# ============================================================
# DUPLICATE PREVENTION
# ============================================================

# Don't save the same number again for this period.
DUPLICATE_COOLDOWN = 30


# ============================================================
# DISPLAY
# ============================================================

SHOW_OCR_CONFIDENCE = True
SAVE_SNAPSHOT = True


# ============================================================
# PLATE VALIDATION
# ============================================================

# Set True for stricter Indian registration-number validation.
# Leave False if your system must support arbitrary countries.
INDIAN_PLATES_ONLY = False