import sqlite3
import sys
from datetime import datetime, UTC
from pathlib import Path

import requests

try:
    from py_clob_client.client import ClobClient
except Exception:
    ClobClient = None

DB = Path(__file__).parent / "trades_v4.db"
GAMMA_API = "https://gamma-api.polymarket.com"


def ensure_close_columns(conn: sqlite3.Connection) -> None:
    c = conn.cursor()
    cols = [r[1] for r in c.execute("PRAGMA table_info(trades)").fetchall()]
    if "closed_ts" not in cols:
        c.execute("ALTER TABLE trades ADD COLUMN closed_ts TEXT")
    if "close_price" not in cols:
        c.execute("ALTER TABLE trades ADD COLUMN close_price REAL")
    if "close_note" not in cols:
        c.execute("ALTER TABLE trades ADD COLUMN close_note TEXT")
    if "realized_pnl" not in cols:
        c.execute("ALTER TABLE trades ADD COLUMN realized_pnl REAL")
    if "trade_token_id" not in cols:
        c.execute("ALTER TABLE trades ADD COLUMN trade_token_id TEXT")
    conn.commit()


def get_quote(slug: str) -> dict | None:
    try:
        r = requests.get(f"{GAMMA_API}/markets", params={"slug": slug, "limit": 1}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list) or not data:
            return None
        m = data[0]

        best_bid = None
        best_ask = None
        yes_last = None

        try:
            if m.get("bestBid") is not None:
                best_bid = float(m.get("bestBid"))
        except Exception:
            pass
        try:
            if m.get("bestAsk") is not None:
                best_ask = float(m.get("bestAsk"))
        except Exception:
            pass
        try:
            if m.get("lastTradePrice") is not None:
                yes_last = float(m.get("lastTradePrice"))
        except Exception:
            pass

        if yes_last is None:
            op = m.get("outcomePrices")
            if isinstance(op, str):
                import json
                op = json.loads(op)
            if isinstance(op, list) and op:
                yes_last = float(op[0])

        return {"best_bid": best_bid, "best_ask": best_ask, "yes_last": yes_last}
    except Exception:
        return None


def fetch_open_trades(conn: sqlite3.Connection):
    c = conn.cursor()
    return c.execute(
        """
        SELECT id, ts, slug, side, entry, size, trade_token_id
        FROM trades
        WHERE closed_ts IS NULL
        ORDER BY id DESC
        """
    ).fetchall()


def choose_trade(open_rows, arg_trade_id: int | None):
    if not open_rows:
        return None

    if arg_trade_id is not None:
        for r in open_rows:
            if int(r[0]) == int(arg_trade_id):
                return r
        return None

    print("Open trades:")
    for i, r in enumerate(open_rows, start=1):
        tid, ts, slug, side, entry, size, trade_token_id = r
        print(f" {i}) id={tid} | {slug} | {side} | entry={float(entry):.4f} | size={float(size):.2f}")

    raw = input("Pick trade number to close (Enter = latest): ").strip()
    if raw == "":
        return open_rows[0]
    try:
        idx = int(raw)
        if 1 <= idx <= len(open_rows):
            return open_rows[idx - 1]
    except Exception:
        pass
    return None


def main() -> int:
    if not DB.exists():
        print("[SELL] trades_v4.db not found.")
        return 1

    conn = sqlite3.connect(DB)
    ensure_close_columns(conn)

    arg_trade_id = None
    if len(sys.argv) > 1:
        try:
            arg_trade_id = int(sys.argv[1])
        except Exception:
            pass

    open_rows = fetch_open_trades(conn)
    chosen = choose_trade(open_rows, arg_trade_id)
    if not chosen:
        print("[SELL] No valid open trade selected.")
        conn.close()
        return 1

    tid, ts, slug, side, entry, size, trade_token_id = chosen
    q = get_quote(slug)
    if q is None:
        print(f"[SELL] Could not fetch live quote for {slug}.")
        conn.close()
        return 1

    # First choice: CLOB executable sell price for the held token.
    close_price = None
    if trade_token_id and ClobClient is not None:
        try:
            clob = ClobClient("https://clob.polymarket.com", chain_id=137)
            qp = clob.get_price(trade_token_id, side="SELL")
            p = float(qp.get("price"))
            if 0 <= p <= 1:
                close_price = p
        except Exception:
            close_price = None

    # Fallback: side-aware Gamma approximation.
    if close_price is None:
        if side == "BUY_YES":
            close_price = q.get("best_bid") if q.get("best_bid") is not None else q.get("yes_last")
        else:
            # Selling NO -> approximate NO bid as (1 - YES ask)
            yes_ask = q.get("best_ask")
            if yes_ask is not None:
                close_price = 1.0 - float(yes_ask)
            else:
                yes_last = q.get("yes_last")
                close_price = (1.0 - float(yes_last)) if yes_last is not None else None

    if close_price is None:
        print(f"[SELL] Could not derive close price for {slug}.")
        conn.close()
        return 1
    pnl = (float(close_price) - float(entry)) * float(size)

    confirm = input(
        f"Close id={tid} {side} @ current {close_price:.4f}? (y/N): "
    ).strip().lower()
    if confirm not in ("y", "yes"):
        print("[SELL] Cancelled.")
        conn.close()
        return 1

    now_iso = datetime.now(UTC).isoformat()
    c = conn.cursor()
    c.execute(
        "UPDATE trades SET closed_ts = ?, close_price = ?, close_note = ?, realized_pnl = ? WHERE id = ?",
        (now_iso, float(close_price), "manual_sell", float(pnl), int(tid)),
    )
    conn.commit()
    conn.close()

    print("[SELL] Position closed.")
    print(f" id={tid} | slug={slug} | side={side}")
    print(f" entry={float(entry):.4f} | close={float(close_price):.4f} | size={float(size):.2f}")
    print(f" realized_pnl={pnl:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
