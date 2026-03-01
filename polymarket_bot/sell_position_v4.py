import sqlite3
import sys
from datetime import datetime, UTC
from pathlib import Path

import requests

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
    conn.commit()


def get_yes_price(slug: str) -> float | None:
    try:
        r = requests.get(f"{GAMMA_API}/markets", params={"slug": slug, "limit": 1}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list) or not data:
            return None
        m = data[0]

        ltp = m.get("lastTradePrice")
        if ltp is not None:
            p = float(ltp)
            if 0 <= p <= 1:
                return p

        op = m.get("outcomePrices")
        if isinstance(op, str):
            import json
            op = json.loads(op)
        if isinstance(op, list) and op:
            p = float(op[0])
            if 0 <= p <= 1:
                return p
    except Exception:
        return None
    return None


def main() -> int:
    if not DB.exists():
        print("[SELL] trades_v4.db not found.")
        return 1

    conn = sqlite3.connect(DB)
    ensure_close_columns(conn)
    c = conn.cursor()

    trade_id = None
    if len(sys.argv) > 1:
        try:
            trade_id = int(sys.argv[1])
        except Exception:
            pass

    if trade_id is None:
        row = c.execute(
            """
            SELECT id, ts, slug, side, entry, size
            FROM trades
            WHERE closed_ts IS NULL
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    else:
        row = c.execute(
            """
            SELECT id, ts, slug, side, entry, size
            FROM trades
            WHERE id = ? AND closed_ts IS NULL
            LIMIT 1
            """,
            (trade_id,),
        ).fetchone()

    if not row:
        print("[SELL] No open trade found (or trade already closed).")
        conn.close()
        return 1

    tid, ts, slug, side, entry, size = row
    yes_now = get_yes_price(slug)
    if yes_now is None:
        print(f"[SELL] Could not fetch live price for {slug}.")
        conn.close()
        return 1

    close_price = yes_now if side == "BUY_YES" else (1.0 - yes_now)
    pnl = (close_price - float(entry)) * float(size)
    now_iso = datetime.now(UTC).isoformat()

    c.execute(
        "UPDATE trades SET closed_ts = ?, close_price = ?, close_note = ? WHERE id = ?",
        (now_iso, float(close_price), "manual_sell", int(tid)),
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
