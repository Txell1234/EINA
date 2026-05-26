import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import settings

path = settings.database_url_sync.replace("sqlite:///", "")
conn = sqlite3.connect(path)
cur = conn.cursor()
cur.execute("PRAGMA table_info(alert_monitors)")
print("alert_monitors:", [r[1] for r in cur.fetchall()])
cur.execute("PRAGMA table_info(alert_matches)")
print("alert_matches:", [r[1] for r in cur.fetchall()])
conn.close()
