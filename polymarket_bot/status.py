import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "trades.db"

if not DB.exists():
    print("No trades.db found yet. Run the bot first.")
    raise SystemExit(0)

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM trades")
total = cur.fetchone()[0]

cur.execute("SELECT COALESCE(SUM(price * size), 0) FROM trades")
notional = float(cur.fetchone()[0] or 0)

cur.execute(
    "SELECT ts, market_id, question, side, price, size, note FROM trades ORDER BY id DESC LIMIT 10"
)
rows = cur.fetchall()
conn.close()

print(f"Total trades: {total}")
print(f"Total notional: ${notional:.2f}")
print("\nLast trades:")
for r in rows:
    ts, market_id, question, side, price, size, note = r
    print(f"- {ts} | {market_id} | {side} @ {price} size={size:.4f} | {note}")
    print(f"  {question}")
