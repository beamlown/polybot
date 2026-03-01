import sqlite3
from pathlib import Path
from typing import Dict, Any

import requests

DB = Path(__file__).parent / "trades_v4.db"
GAMMA_API = "https://gamma-api.polymarket.com"

# ANSI colors (works in modern Windows Terminal/CMD)
RST = "\033[0m"
GRN = "\033[92m"
RED = "\033[91m"
YLW = "\033[93m"
CYN = "\033[96m"
WHT = "\033[97m"


def c(text: str, color: str) -> str:
    return f"{color}{text}{RST}"


def get_market(slug: str, cache: Dict[str, Dict[str, Any]]) -> Dict[str, Any] | None:
    if slug in cache:
        return cache[slug]
    try:
        r = requests.get(f"{GAMMA_API}/markets", params={"slug": slug, "limit": 1}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            cache[slug] = data[0]
            return data[0]
    except Exception:
        pass
    cache[slug] = None
    return None


def to_float(x, default=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def format_cents(px: float) -> str:
    return f"{px * 100:.1f}c"


if not DB.exists():
    print(c("[PNL] trades_v4.db not found yet.", RED))
    raise SystemExit(1)

conn = sqlite3.connect(DB)
cursor = conn.cursor()
rows = cursor.execute(
    """
    SELECT id, ts, slug, side, entry, size, edge
    FROM trades
    ORDER BY id DESC
    LIMIT 50
    """
).fetchall()
count = int(cursor.execute("SELECT COUNT(*) FROM trades").fetchone()[0] or 0)
conn.close()

market_cache: Dict[str, Dict[str, Any]] = {}

print("=" * 92)
print(c("POLYMARKET V4 LIVE PNL", CYN))
print("=" * 92)
print(f"Total entries in DB: {count}")
print("Legend: BUY_YES = bought UP (YES), BUY_NO = bought DOWN (NO)")
print("-" * 92)

if not rows:
    print(c("No entries yet.", YLW))
    raise SystemExit(0)

# Header
print(f"{'ID':<5} {'Round':<26} {'Bet':<18} {'Entry':<10} {'Now':<10} {'Size':<8} {'PnL $':<12} {'PnL %':<8}")
print("-" * 92)

total_live_pnl = 0.0
priced_rows = 0

for r in rows:
    trade_id, ts, slug, side, entry, size, edge = r
    entry = to_float(entry)
    size = to_float(size)

    bet_label = "UP" if side == "BUY_YES" else ("DOWN" if side == "BUY_NO" else side)
    bet_text = f"{side} ({bet_label})"

    m = get_market(slug, market_cache)
    now_px = None

    if m is not None:
        yes_price = to_float(m.get("lastTradePrice"), default=-1.0)
        if yes_price < 0 or yes_price > 1:
            op = m.get("outcomePrices")
            if isinstance(op, str):
                try:
                    import json
                    op = json.loads(op)
                except Exception:
                    op = None
            if isinstance(op, list) and op:
                yes_price = to_float(op[0], default=-1.0)

        if 0 <= yes_price <= 1:
            now_px = yes_price if side == "BUY_YES" else (1.0 - yes_price)

    if now_px is None:
        now_txt = c("n/a", YLW)
        pnl_txt = c("n/a", YLW)
        pnl_pct_txt = c("n/a", YLW)
    else:
        priced_rows += 1
        pnl = (now_px - entry) * size
        pnl_pct = ((now_px - entry) / entry * 100.0) if entry > 0 else 0.0
        total_live_pnl += pnl

        color = GRN if pnl >= 0 else RED
        now_txt = c(format_cents(now_px), color)
        pnl_txt = c(f"{pnl:+.2f}", color)
        pnl_pct_txt = c(f"{pnl_pct:+.1f}%", color)

    entry_txt = format_cents(entry)
    print(f"{trade_id:<5} {slug[:26]:<26} {bet_text:<18} {entry_txt:<10} {now_txt:<10} {size:<8.2f} {pnl_txt:<12} {pnl_pct_txt:<8}")

print("-" * 92)
if priced_rows > 0:
    total_color = GRN if total_live_pnl >= 0 else RED
    print(f"Live marked PnL (priced rows): {c(f'{total_live_pnl:+.2f}', total_color)}")
else:
    print(c("No rows could be priced from live market data.", YLW))

print(c("Tip: reset trade log with reset_trades_v4.bat if you want a clean slate.", WHT))
