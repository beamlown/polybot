import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "trades_v3.db"

print("Latest Entries (newest first):")
print("-" * 70)

if not DB.exists():
    print("No trades_v3.db found yet.")
    raise SystemExit(0)

conn = sqlite3.connect(DB)
c = conn.cursor()
rows = c.execute(
    "select id, ts, slug, side, entry, size, edge from trades order by id desc limit 8"
).fetchall()
conn.close()

if not rows:
    print("No entries yet.")
else:
    for r in rows:
        print(f"#{r[0]}  {r[1]}")
        print(f"   round: {r[2]}")
        print(f"   side : {r[3]}  entry: {r[4]:.4f}  size: {r[5]:.2f}  edge: {r[6]:.4f}")
        print("-" * 70)
