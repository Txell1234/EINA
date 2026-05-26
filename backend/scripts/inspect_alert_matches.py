import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parents[1] / "osint_platform.db"
c = sqlite3.connect(db)
print("total alert_matches", c.execute("SELECT COUNT(*) FROM alert_matches").fetchone()[0])
print("monitors with desync (match_count>0 but 0 rows):")
for row in c.execute(
    """
    SELECT m.id, m.match_count, m.indicator,
           (SELECT COUNT(*) FROM alert_matches a WHERE a.monitor_id = m.id) AS actual
    FROM alert_monitors m
    WHERE m.match_count > 0
    """
):
    if row[3] == 0:
        print(f"  id={row[0]} count={row[1]} actual=0 ind={row[2][:60]!r}")
