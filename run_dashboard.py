import uvicorn
import webbrowser
import threading
import time
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

from backend.database import init_db
from backend.seed_data import seed_database

def open_browser():
    time.sleep(1.5)
    print("\n" + "=" * 60)
    print(">> DRISHTI-SUTRA COMMAND CENTER ONLINE")
    print(">> Open your browser at: http://localhost:8000")
    print("=" * 60 + "\n")
    try:
        webbrowser.open("http://localhost:8000")
    except Exception as e:
        print(f"Browser launch notice: {e}")

if __name__ == "__main__":
    print("Initializing Drishti-Sutra City-Wide ANPR Engine...")
    init_db()
    seed_database(force=False)

    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(
        "backend.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )
