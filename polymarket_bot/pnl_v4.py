import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "trades_v4.db"

if not DB.exists():
    print("[PNL] trades_v4.db not found yet.")
    raise SystemExit(1)

conn = sqlite3.connect(DB)
c = conn.cursor()

rows = c.execute(
    """
    SELECT id, ts, slug, side, entry, size, edge
    FROM trades
    ORDER BY id DESC
    LIMIT 30
    """
).fetchall()

count = c.execute("SELECT COUNT(*) FROM trades").fetchone()[0]

# Paper estimate: edge * size (not realized settlement PnL)
edge_pnl = c.execute("SELECT COALESCE(SUM(edge * size), 0.0) FROM trades").fetchone()[0]

conn.close()

print("=" * 72)
print("POLYMARKET V4 PNL SNAPSHOT (PAPER ESTIMATE)")
print("=" * 72)
print(f"Total entries: {count}")
print(f"Edge-based PnL estimate: ${edge_pnl:.2f}")
print("-" * 72)

if not rows:
    print("No trades yet.")
else:
    for r in rows:
        print(f"#{r[0]}  {r[1]}")
        print(f"   round: {r[2]}")
        print(f"   side : {r[3]}  entry: {r[4]:.4f}  size: {r[5]:.2f}  edge: {r[6]:.4f}")
        print("-" * 72)
