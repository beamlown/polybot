import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import requests

DB = Path(__file__).parent / "trades.db"
ARCHIVE_DIR = Path(__file__).parent / "cashout_archive"
BASE_URL = "https://gamma-api.polymarket.com"


def fetch_market_snapshot(market_id: str) -> dict:
    try:
        resp = requests.get(
            f"{BASE_URL}/markets",
            params={"id": str(market_id)},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list) or not data:
            return {"yes_price": None}

        m = data[0]
        raw_prices = m.get("outcomePrices")
        yes_price = None
        if isinstance(raw_prices, list) and raw_prices:
            yes_price = float(raw_prices[0])
        elif isinstance(raw_prices, str) and raw_prices:
            import json
            arr = json.loads(raw_prices)
            if isinstance(arr, list) and arr:
                yes_price = float(arr[0])
        return {"yes_price": yes_price}
    except Exception:
        return {"yes_price": None}

if not DB.exists():
    print("No trades.db found. Nothing to cash out.")
    raise SystemExit(0)

conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT market_id, question, side, price, size FROM trades WHERE side IN ('BUY_YES','BUY_NO')")
rows = cur.fetchall()
conn.close()

if not rows:
    print("No open paper positions.")
    raise SystemExit(0)

positions = {}
for market_id, question, side, price, size in rows:
    k = f"{market_id}:{side}"
    if k not in positions:
        positions[k] = {"market_id": str(market_id), "question": question, "side": side, "qty": 0.0, "cost": 0.0}
    positions[k]["qty"] += float(size)
    positions[k]["cost"] += float(price) * float(size)

portfolio_pnl = 0.0
print("Paper Cash Out Summary")
print("-" * 50)
for p in positions.values():
    qty = p["qty"]
    avg_entry = p["cost"] / qty if qty else 0.0
    snap = fetch_market_snapshot(p["market_id"])
    yes_price = snap["yes_price"]
    if yes_price is None:
        print(f"{p['market_id']} [{p['side']}] -> skipped (no live mark)")
        continue

    current = yes_price if p["side"] == "BUY_YES" else (1.0 - yes_price)
    pnl = (current - avg_entry) * qty
    portfolio_pnl += pnl
    print(f"{p['market_id']} [{p['side']}] pnl=${pnl:.2f} entry={avg_entry:.4f} mark={current:.4f}")

print("-" * 50)
print(f"TOTAL REALIZED (paper): ${portfolio_pnl:.2f}")

ARCHIVE_DIR.mkdir(exist_ok=True)
ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
archived = ARCHIVE_DIR / f"trades_{ts}.db"
shutil.copy2(DB, archived)
DB.unlink(missing_ok=True)
print(f"Archived old trades DB -> {archived}")
print("Reset complete. New session starts empty.")
