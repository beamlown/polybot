import sqlite3
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any

import requests

try:
    from py_clob_client.client import ClobClient
except Exception:
    ClobClient = None

DB = Path(__file__).parent / "trades_v4.db"
GAMMA_API = "https://gamma-api.polymarket.com"
CLOSED_HIDE_AFTER_SECONDS = 300
STARTING_BANKROLL = 2000.0

RST = "\033[0m"
GRN = "\033[92m"
RED = "\033[91m"
YLW = "\033[93m"
CYN = "\033[96m"
WHT = "\033[97m"


def c(text: str, color: str) -> str:
    return f"{color}{text}{RST}"


def to_float(x, default=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def format_cents(px: float) -> str:
    return f"{px * 100:.1f}c"


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


def _extract_yes_prices(m: Dict[str, Any]) -> tuple[float | None, float | None, float | None]:
    yes_bid = to_float(m.get("bestBid"), default=-1.0)
    yes_ask = to_float(m.get("bestAsk"), default=-1.0)
    yes_last = to_float(m.get("lastTradePrice"), default=-1.0)

    if (yes_last < 0 or yes_last > 1):
        op = m.get("outcomePrices")
        if isinstance(op, str):
            try:
                import json
                op = json.loads(op)
            except Exception:
                op = None
        if isinstance(op, list) and op:
            yes_last = to_float(op[0], default=-1.0)

    yes_bid = yes_bid if 0 <= yes_bid <= 1 else None
    yes_ask = yes_ask if 0 <= yes_ask <= 1 else None
    yes_last = yes_last if 0 <= yes_last <= 1 else None
    return yes_bid, yes_ask, yes_last


def get_clob_exec_mark(token_id: str | None, clob_client) -> float | None:
    if not token_id or clob_client is None:
        return None
    try:
        q = clob_client.get_price(token_id, side="SELL")
        p = to_float(q.get("price"), default=-1.0)
        return p if 0 <= p <= 1 else None
    except Exception:
        return None


def get_clob_buy_up_down(slug: str, cache: Dict[str, Dict[str, Any]], clob_client) -> tuple[float | None, float | None]:
    if clob_client is None:
        return None, None
    m = get_market(slug, cache)
    if not m:
        return None, None

    raw = m.get("clobTokenIds")
    yes_id = None
    no_id = None
    try:
        if isinstance(raw, str):
            import json
            raw = json.loads(raw)
        if isinstance(raw, list) and len(raw) >= 2:
            yes_id = str(raw[0])
            no_id = str(raw[1])
    except Exception:
        return None, None

    buy_up = None
    buy_down = None
    try:
        if yes_id:
            qy = clob_client.get_price(yes_id, side="BUY")
            py = to_float(qy.get("price"), default=-1.0)
            if 0 <= py <= 1:
                buy_up = py
    except Exception:
        pass
    try:
        if no_id:
            qn = clob_client.get_price(no_id, side="BUY")
            pn = to_float(qn.get("price"), default=-1.0)
            if 0 <= pn <= 1:
                buy_down = pn
    except Exception:
        pass

    return buy_up, buy_down


def get_price_views(slug: str, side: str, cache: Dict[str, Dict[str, Any]]) -> tuple[float | None, float | None, float | None, float | None]:
    m = get_market(slug, cache)
    if m is None:
        return None, None, None, None

    yes_bid, yes_ask, yes_last = _extract_yes_prices(m)

    buy_up = yes_ask if yes_ask is not None else yes_last
    buy_down = (1.0 - yes_bid) if yes_bid is not None else ((1.0 - yes_last) if yes_last is not None else None)

    # UI-ish mark: last/outcome-based
    ui_mark = yes_last if side == "BUY_YES" else ((1.0 - yes_last) if yes_last is not None else None)

    # Executable-ish mark: bid side for what we'd sell now
    if side == "BUY_YES":
        exec_mark = yes_bid if yes_bid is not None else yes_last
    else:
        exec_mark = (1.0 - yes_ask) if yes_ask is not None else ((1.0 - yes_last) if yes_last is not None else None)

    return ui_mark, exec_mark, buy_up, buy_down


if not DB.exists():
    print(c("[PNL] trades_v4.db not found yet.", RED))
    raise SystemExit(1)

conn = sqlite3.connect(DB)
cursor = conn.cursor()

cols = [r[1] for r in cursor.execute("PRAGMA table_info(trades)").fetchall()]
has_closed = "closed_ts" in cols
has_realized = "realized_pnl" in cols
has_trade_token = "trade_token_id" in cols

select_sql = "SELECT id, ts, slug, side, entry, size"
if has_trade_token:
    select_sql += ", trade_token_id"
if has_closed:
    select_sql += ", closed_ts"
if has_realized:
    select_sql += ", realized_pnl"
select_sql += " FROM trades ORDER BY id DESC LIMIT 80"
rows = cursor.execute(select_sql).fetchall()

count = int(cursor.execute("SELECT COUNT(*) FROM trades").fetchone()[0] or 0)
all_time_realized = 0.0
if has_realized:
    all_time_realized = float(cursor.execute("SELECT COALESCE(SUM(realized_pnl), 0.0) FROM trades WHERE closed_ts IS NOT NULL").fetchone()[0] or 0.0)
conn.close()

# Load starting bankroll from .env if available
try:
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip().startswith("STARTING_BANKROLL="):
                STARTING_BANKROLL = float(line.split("=", 1)[1].strip() or "2000")
                break
except Exception:
    pass

market_cache: Dict[str, Dict[str, Any]] = {}
clob = ClobClient("https://clob.polymarket.com", chain_id=137) if ClobClient is not None else None

print("=" * 146)
print(c("POLYMARKET V4 LIVE PNL", CYN))
print("=" * 146)
print(f"Total entries in DB: {count}")
print("Legend: BUY_YES = bought UP (YES), BUY_NO = bought DOWN (NO)")
print("-" * 146)
print(f"{'ID':<5} {'Status':<8} {'Round':<26} {'Bet':<18} {'Entry':<10} {'UI Mark':<10} {'Exec Mark':<10} {'Buy UP':<10} {'Buy DOWN':<10} {'Size':<8} {'PnL $':<12} {'PnL %':<8}")
print("-" * 146)

open_unrealized_total = 0.0
realized_total = 0.0
priced_open_rows = 0

now_utc = datetime.now(UTC)

for r in rows:
    idx = 0
    trade_id = r[idx]; idx += 1
    ts = r[idx]; idx += 1
    slug = r[idx]; idx += 1
    side = r[idx]; idx += 1
    entry = to_float(r[idx]); idx += 1
    size = to_float(r[idx]); idx += 1
    trade_token_id = r[idx] if has_trade_token else None
    if has_trade_token:
        idx += 1
    closed_ts = r[idx] if has_closed else None
    if has_closed:
        idx += 1
    realized_pnl = to_float(r[idx], default=0.0) if has_realized else 0.0

    is_closed = bool(closed_ts)
    bet_label = "UP" if side == "BUY_YES" else ("DOWN" if side == "BUY_NO" else side)
    bet_text = f"{side} ({bet_label})"

    if is_closed:
        # Hide closed trades after a short window to keep monitor focused on active risk.
        try:
            closed_dt = datetime.fromisoformat(str(closed_ts).replace("Z", "+00:00"))
            if closed_dt.tzinfo is None:
                closed_dt = closed_dt.replace(tzinfo=UTC)
            if (now_utc - closed_dt).total_seconds() > CLOSED_HIDE_AFTER_SECONDS:
                continue
        except Exception:
            pass

        status = c("CLOSED", YLW)
        ui_txt = c("closed", YLW)
        exec_txt = c("closed", YLW)
        buy_up_txt = c("-", YLW)
        buy_down_txt = c("-", YLW)
        pnl = realized_pnl
        pnl_pct = (pnl / (entry * size) * 100.0) if entry > 0 and size > 0 else 0.0
        realized_total += pnl
        color = GRN if pnl >= 0 else RED
        pnl_txt = c(f"{pnl:+.2f}", color)
        pnl_pct_txt = c(f"{pnl_pct:+.1f}%", color)
    else:
        status = c("OPEN", CYN)
        ui_px, exec_px, buy_up_px, buy_down_px = get_price_views(slug, side, market_cache)
        clob_buy_up, clob_buy_down = get_clob_buy_up_down(slug, market_cache, clob)
        if clob_buy_up is not None:
            buy_up_px = clob_buy_up
        if clob_buy_down is not None:
            buy_down_px = clob_buy_down

        clob_exec = get_clob_exec_mark(trade_token_id, clob)
        # Safety: only trust CLOB token mark when it's reasonably close to Gamma-derived executable view.
        if clob_exec is not None:
            if exec_px is None or abs(clob_exec - exec_px) <= 0.15:
                exec_px = clob_exec
        ui_txt = c("n/a", YLW) if ui_px is None else c(format_cents(ui_px), WHT)
        buy_up_txt = c("n/a", YLW) if buy_up_px is None else c(format_cents(buy_up_px), CYN)
        buy_down_txt = c("n/a", YLW) if buy_down_px is None else c(format_cents(buy_down_px), CYN)

        if exec_px is None:
            exec_txt = c("n/a", YLW)
            pnl_txt = c("n/a", YLW)
            pnl_pct_txt = c("n/a", YLW)
        else:
            pnl = (exec_px - entry) * size
            pnl_pct = ((exec_px - entry) / entry * 100.0) if entry > 0 else 0.0
            open_unrealized_total += pnl
            priced_open_rows += 1
            color = GRN if pnl >= 0 else RED
            exec_txt = c(format_cents(exec_px), color)
            pnl_txt = c(f"{pnl:+.2f}", color)
            pnl_pct_txt = c(f"{pnl_pct:+.1f}%", color)

    print(f"{trade_id:<5} {status:<8} {slug[:26]:<26} {bet_text:<18} {format_cents(entry):<10} {ui_txt:<10} {exec_txt:<10} {buy_up_txt:<10} {buy_down_txt:<10} {size:<8.2f} {pnl_txt:<12} {pnl_pct_txt:<8}")

print("-" * 146)
rt_color = GRN if realized_total >= 0 else RED
all_rt_color = GRN if all_time_realized >= 0 else RED
ut_color = GRN if open_unrealized_total >= 0 else RED
print(f"Realized PnL (visible window): {c(f'{realized_total:+.2f}', rt_color)}")
print(f"Realized PnL (all-time):       {c(f'{all_time_realized:+.2f}', all_rt_color)}")
print(f"Unrealized PnL:                {c(f'{open_unrealized_total:+.2f}', ut_color)} (priced open rows={priced_open_rows})")
net_pnl = all_time_realized + open_unrealized_total
est_balance = STARTING_BANKROLL + net_pnl
print(f"Net PnL (all-time+open):       {c(f'{net_pnl:+.2f}', GRN if net_pnl >= 0 else RED)}")
print(f"Est. Balance:                  {c(f'${est_balance:,.2f}', GRN if est_balance >= STARTING_BANKROLL else RED)} (start=${STARTING_BANKROLL:,.2f})")
print(c(f"Closed rows older than {CLOSED_HIDE_AFTER_SECONDS}s are hidden from this live screen.", WHT))
print(c("Tip: use sell_position_v4.bat to pick and close a specific open trade.", WHT))
