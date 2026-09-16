import sqlite3
import os
from pathlib import Path
import pandas as pd
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "anpr_city.db"
OUTPUT_DIR = BASE_DIR / "output"
EXCEL_PATH = OUTPUT_DIR / "vehicle_data.xlsx"

def _write_workbook(filepath: str, df_detections, df_cameras, df_blacklist, df_alerts, df_identities):
    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        df_detections.to_excel(writer, sheet_name="Detections", index=False)
        df_cameras.to_excel(writer, sheet_name="Cameras", index=False)
        df_blacklist.to_excel(writer, sheet_name="Watchlist", index=False)
        df_alerts.to_excel(writer, sheet_name="Security Alerts", index=False)
        df_identities.to_excel(writer, sheet_name="Vehicle Identities", index=False)

        workbook = writer.book
        for sheetname in workbook.sheetnames:
            worksheet = workbook[sheetname]
            for col in worksheet.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    val_str = str(cell.value or '')
                    if len(val_str) > max_len:
                        max_len = len(val_str)
                worksheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 50)

def export_database_to_excel(output_path: Path = None) -> Path:
    """
    Exports all database tables from SQLite into a structured, multi-sheet Excel file.
    Handles PermissionError gracefully if the primary file is locked/open in Excel.
    """
    if output_path is None:
        output_path = EXCEL_PATH

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        from backend.database import init_db
        init_db()

    conn = sqlite3.connect(str(DB_PATH))

    try:
        df_detections = pd.read_sql_query("SELECT * FROM detections ORDER BY id DESC", conn)
        df_cameras = pd.read_sql_query("SELECT * FROM cameras ORDER BY id ASC", conn)
        df_blacklist = pd.read_sql_query("SELECT * FROM blacklist ORDER BY date_added DESC", conn)
        df_alerts = pd.read_sql_query("SELECT * FROM alerts ORDER BY id DESC", conn)
        df_identities = pd.read_sql_query("SELECT * FROM vehicle_identities ORDER BY sightings_count DESC", conn)
    finally:
        conn.close()

    try:
        _write_workbook(str(output_path), df_detections, df_cameras, df_blacklist, df_alerts, df_identities)
        return output_path
    except PermissionError:
        # File is currently open in Microsoft Excel! Save to fallback export file
        fallback_path = output_path.parent / "vehicle_data_export.xlsx"
        _write_workbook(str(fallback_path), df_detections, df_cameras, df_blacklist, df_alerts, df_identities)
        return fallback_path

def open_excel_file(output_path: Path = None):
    """
    Ensures Excel file exists and attempts to open it in the OS default spreadsheet application.
    """
    target_path = export_database_to_excel(output_path)
    if os.name == 'nt':
        os.startfile(str(target_path))
    else:
        import subprocess
        subprocess.call(["open" if sys.platform == "darwin" else "xdg-open", str(target_path)])
    return target_path

if __name__ == "__main__":
    path = export_database_to_excel()
    print(f"Successfully exported database to: {path}")
