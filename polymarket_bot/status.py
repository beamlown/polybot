import sqlite3
from pathlib import Path

import requests

DB = Path(__file__).parent / "trades.db"
BASE_URL = "https://gamma-api.polymarket.com"


def money_emoji(value: float) -> str:
    if value > 0:
        return f"🟢 +${value:.2f}"
    if value < 0:
        return f"🔴 -${abs(value):.2f}"
    return "$0.00"


def pct_emoji(value: float) -> str:
    if value > 0:
        return f"🟢 +{value:.2f}%"
    if value < 0:
        return f"🔴 -{abs(value):.2f}%"
    return "0.00%"


def fetch_market_snapshot(market_id: str) -> dict:
    """
    Returns best-effort snapshot:
    {
      yes_price: float|None,
      closed: bool|None,
      mark_source: str
    }
    """
    try:
        resp = requests.get(
            f"{BASE_URL}/markets",
            params={"id": str(market_id)},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list) or not data:
            return {"yes_price": None, "closed": None, "mark_source": "missing"}

        m = data[0]
        raw_prices = m.get("outcomePrices")
        yes_price = None
        if isinstance(raw_prices, list) and raw_prices:
            try:
                yes_price = float(raw_prices[0])
            except Exception:
                yes_price = None
        elif isinstance(raw_prices, str) and raw_prices:
            # fallback if API returns stringified list
            import json
            try:
                arr = json.loads(raw_prices)
                if isinstance(arr, list) and arr:
                    yes_price = float(arr[0])
            except Exception:
                yes_price = None

        closed = m.get("closed")
        source = "resolved" if closed else "live"
        return {"yes_price": yes_price, "closed": closed, "mark_source": source}
    except Exception:
        return {"yes_price": None, "closed": None, "mark_source": "unavailable"}


if not DB.exists():
    print("No trades.db found yet. Run the bot first.")
    raise SystemExit(0)

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM trades")
total = int(cur.fetchone()[0] or 0)

cur.execute("SELECT COALESCE(SUM(price * size), 0) FROM trades")
notional = float(cur.fetchone()[0] or 0)

cur.execute(
    "SELECT market_id, question, side, price, size FROM trades WHERE side IN ('BUY_YES','BUY_NO')"
)
positions_raw = cur.fetchall()

cur.execute(
    "SELECT ts, market_id, question, side, price, size, note FROM trades ORDER BY id DESC LIMIT 10"
)
recent_rows = cur.fetchall()
conn.close()

positions = {}
for market_id, question, side, price, size in positions_raw:
    k = f"{market_id}:{side}"
    if k not in positions:
        positions[k] = {
            "market_id": str(market_id),
            "side": side,
            "question": question,
            "qty": 0.0,
            "cost": 0.0,
        }
    positions[k]["qty"] += float(size)
    positions[k]["cost"] += float(price) * float(size)

position_rows = []
portfolio_pnl = 0.0

for _, p in positions.items():
    qty = p["qty"]
    cost = p["cost"]
    avg_entry = (cost / qty) if qty else 0.0

    snap = fetch_market_snapshot(p["market_id"])
    yes_price = snap["yes_price"]
    closed = snap["closed"]

    if yes_price is None:
        pnl = 0.0
        pnl_pct = 0.0
        mark = "N/A"
        status = "unknown"
    else:
        if p["side"] == "BUY_YES":
            current = yes_price
        else:
            current = 1.0 - yes_price

        pnl = (current - avg_entry) * qty
        pnl_pct = ((current - avg_entry) / avg_entry * 100.0) if avg_entry > 0 else 0.0
        mark = f"{current:.4f}"
        status = "resolved" if closed else "live"

    portfolio_pnl += pnl
    position_rows.append(
        {
            "market_id": p["market_id"],
            "side": p["side"],
            "question": p["question"],
            "qty": qty,
            "avg_entry": avg_entry,
            "mark": mark,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "status": status,
        }
    )

position_rows.sort(key=lambda x: x["pnl"], reverse=True)

print("=" * 64)
print("POLYMARKET PAPER BOT STATUS")
print("=" * 64)
print(f"Total trades           : {total}")
print(f"Total notional         : ${notional:.2f}")
print(f"Portfolio unrealized   : {money_emoji(portfolio_pnl)}")
print("=" * 64)

print("\nPOSITIONS (BEST -> WORST)")
print("-" * 64)
if not position_rows:
    print("- No open paper positions yet.")
else:
    for row in position_rows:
        pnl_str = money_emoji(row["pnl"])
        pct_str = pct_emoji(row["pnl_pct"])
        print(f"{row['market_id']} [{row['side']}]  |  {pnl_str} ({pct_str})")
        print(f"  qty={row['qty']:.2f}  entry={row['avg_entry']:.4f}  mark={row['mark']}  status={row['status']}")
        print(f"  {row['question']}")
        print()

print("\nRECENT TRADES (LATEST 10)")
print("-" * 64)
for r in recent_rows:
    ts, market_id, question, side, price, size, note = r
    print(f"{ts}  |  {market_id}  |  {side}")
    print(f"  entry={price}  size={size:.2f}  note={note}")
    print(f"  {question}")
    print()
