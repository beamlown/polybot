import json
import sqlite3
from pathlib import Path

import requests

DB = Path(__file__).parent / "trades.db"
BASE_URL = "https://gamma-api.polymarket.com"

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def color_money(value: float) -> str:
    if value > 0:
        return f"{GREEN}${value:.2f}{RESET}"
    if value < 0:
        return f"{RED}-${abs(value):.2f}{RESET}"
    return f"${value:.2f}"


def fetch_market_prices(limit: int = 300) -> dict[str, float]:
    try:
        resp = requests.get(
            f"{BASE_URL}/events",
            params={"closed": "false", "limit": limit},
            timeout=20,
        )
        resp.raise_for_status()
        events = resp.json()
    except Exception:
        return {}

    prices: dict[str, float] = {}
    if not isinstance(events, list):
        return prices

    for event in events:
        for market in event.get("markets", []) or []:
            market_id = str(market.get("id") or market.get("conditionId") or market.get("slug") or "")
            if not market_id:
                continue

            outcome_prices = market.get("outcomePrices")
            if isinstance(outcome_prices, str):
                try:
                    outcome_prices = json.loads(outcome_prices)
                except Exception:
                    outcome_prices = []

            if isinstance(outcome_prices, list) and outcome_prices:
                try:
                    prices[market_id] = float(outcome_prices[0])
                except Exception:
                    pass

    return prices


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
    "SELECT market_id, question, price, size FROM trades WHERE side='BUY_YES'"
)
positions_raw = cur.fetchall()

cur.execute(
    "SELECT ts, market_id, question, side, price, size, note FROM trades ORDER BY id DESC LIMIT 10"
)
recent_rows = cur.fetchall()
conn.close()

# Aggregate positions by market
positions: dict[str, dict] = {}
for market_id, question, price, size in positions_raw:
    k = str(market_id)
    if k not in positions:
        positions[k] = {
            "question": question,
            "qty": 0.0,
            "cost": 0.0,
        }
    positions[k]["qty"] += float(size)
    positions[k]["cost"] += float(price) * float(size)

prices = fetch_market_prices()
position_rows = []
portfolio_pnl = 0.0

for market_id, p in positions.items():
    qty = p["qty"]
    cost = p["cost"]
    avg_entry = (cost / qty) if qty else 0.0
    current = prices.get(market_id)

    if current is None:
        pnl = 0.0
        pnl_pct = 0.0
        mark = "N/A"
    else:
        pnl = (current - avg_entry) * qty
        pnl_pct = ((current - avg_entry) / avg_entry * 100.0) if avg_entry > 0 else 0.0
        mark = f"{current:.4f}"

    portfolio_pnl += pnl
    position_rows.append(
        {
            "market_id": market_id,
            "question": p["question"],
            "qty": qty,
            "avg_entry": avg_entry,
            "mark": mark,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
        }
    )

position_rows.sort(key=lambda x: x["pnl"], reverse=True)

print("=" * 64)
print("POLYMARKET PAPER BOT STATUS")
print("=" * 64)
print(f"Total trades           : {total}")
print(f"Total notional         : ${notional:.2f}")
print(f"Portfolio unrealized   : {color_money(portfolio_pnl)}")
print("=" * 64)

print("\nPOSITIONS (BEST -> WORST)")
print("-" * 64)
if not position_rows:
    print("- No open paper positions yet.")
else:
    for row in position_rows:
        pnl_str = color_money(row["pnl"])
        pct = f"{row['pnl_pct']:+.2f}%"
        if row["pnl_pct"] > 0:
            pct = f"{GREEN}{pct}{RESET}"
        elif row["pnl_pct"] < 0:
            pct = f"{RED}{pct}{RESET}"

        print(f"{row['market_id']}  |  pnl={pnl_str} ({pct})")
        print(f"  qty={row['qty']:.2f}  entry={row['avg_entry']:.4f}  mark={row['mark']}")
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
