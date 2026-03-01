import sqlite3
import time
from pathlib import Path

DB = Path(__file__).parent / "trades_v4.db"
STARTING_BANKROLL = 2000.0


def load_starting_bankroll() -> float:
    env = Path(__file__).parent / ".env"
    if not env.exists():
        return STARTING_BANKROLL
    try:
        for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip().startswith("STARTING_BANKROLL="):
                return float(line.split("=", 1)[1].strip() or "2000")
    except Exception:
        pass
    return STARTING_BANKROLL


def fetch_snapshot(conn: sqlite3.Connection):
    c = conn.cursor()
    cols = [r[1] for r in c.execute("PRAGMA table_info(trades)").fetchall()]
    has_closed = "closed_ts" in cols
    has_realized = "realized_pnl" in cols
    has_remaining = "remaining_size" in cols

    total = int(c.execute("SELECT COUNT(*) FROM trades").fetchone()[0] or 0)

    if has_closed and has_remaining:
        open_count = int(c.execute("SELECT COUNT(*) FROM trades WHERE closed_ts IS NULL AND COALESCE(remaining_size,size)>0").fetchone()[0] or 0)
    elif has_closed:
        open_count = int(c.execute("SELECT COUNT(*) FROM trades WHERE closed_ts IS NULL").fetchone()[0] or 0)
    else:
        open_count = 0

    realized = 0.0
    if has_realized and has_closed:
        realized = float(c.execute("SELECT COALESCE(SUM(realized_pnl),0) FROM trades WHERE closed_ts IS NOT NULL").fetchone()[0] or 0.0)

    open_rows = []
    if has_closed and has_remaining:
        open_rows = c.execute(
            """
            SELECT id, slug, side, entry, COALESCE(remaining_size,size)
            FROM trades
            WHERE closed_ts IS NULL AND COALESCE(remaining_size,size)>0
            ORDER BY id DESC
            LIMIT 6
            """
        ).fetchall()

    recent_events = []
    if has_closed:
        recent_events = c.execute(
            """
            SELECT id, slug, side, close_note, COALESCE(realized_pnl,0)
            FROM trades
            WHERE closed_ts IS NOT NULL
            ORDER BY id DESC
            LIMIT 8
            """
        ).fetchall()

    last_trade = c.execute(
        "SELECT id, slug, side, entry, size, ts FROM trades ORDER BY id DESC LIMIT 1"
    ).fetchone()

    return {
        "total": total,
        "open_count": open_count,
        "realized": realized,
        "open_rows": open_rows,
        "recent_events": recent_events,
        "last_trade": last_trade,
    }


def fmt_cents(v: float) -> str:
    return f"{float(v)*100:.1f}c"


def render(s: dict, start_balance: float):
    net = s["realized"]
    balance = start_balance + net
    print("=" * 90)
    print("POLYMARKET V4 DASHBOARD (single-screen)")
    print("=" * 90)
    print(f"Total Trades: {s['total']}   Open Positions: {s['open_count']}   Net Realized: {net:+.2f}   Est Balance: ${balance:,.2f}")
    print("-" * 90)

    lt = s["last_trade"]
    if lt:
        print(f"Last Trade: id={lt[0]} | {lt[1]} | {lt[2]} | entry={fmt_cents(lt[3])} | size={float(lt[4]):.2f} | {lt[5]}")
    else:
        print("Last Trade: n/a")

    print("-" * 90)
    print("OPEN POSITIONS")
    if not s["open_rows"]:
        print("  (none)")
    else:
        for r in s["open_rows"]:
            print(f"  id={r[0]} | {r[1]} | {r[2]} | entry={fmt_cents(r[3])} | rem_size={float(r[4]):.2f}")

    print("-" * 90)
    print("RECENT CLOSE EVENTS")
    if not s["recent_events"]:
        print("  (none)")
    else:
        for e in s["recent_events"]:
            print(f"  id={e[0]} | {e[1]} | {e[2]} | {e[3]} | pnl={float(e[4]):+.2f}")

    print("-" * 90)
    print("Refresh: 2s  |  Ctrl+C to exit")


def main():
    start_balance = load_starting_bankroll()
    if not DB.exists():
        print("trades_v4.db not found yet.")
        return

    conn = sqlite3.connect(DB)
    try:
        while True:
            snap = fetch_snapshot(conn)
            print("\033[2J\033[H", end="")
            render(snap, start_balance)
            time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        conn.close()


if __name__ == "__main__":
    main()
