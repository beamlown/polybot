import os
import sqlite3
import time
from datetime import datetime

from dotenv import load_dotenv

from v2_market_discovery import discover_current_round
from v2_signal import get_prob_up

load_dotenv()

STARTING_BANKROLL = float(os.getenv("STARTING_BANKROLL", "2000"))
MIN_EDGE = float(os.getenv("MIN_EDGE", "0.05"))
MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", "5"))
RISK_PCT = float(os.getenv("MAX_RISK_PER_TRADE_PCT", "0.005"))
LOOP_SECONDS = int(os.getenv("LOOP_SECONDS", "5"))
SERIES_PREFIX = os.getenv("SERIES_PREFIX", "btc-updown")
ROUND_MINUTES = int(os.getenv("ROUND_MINUTES", "5"))
DB = "trades_v2.db"


def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            slug TEXT,
            market_id TEXT,
            side TEXT,
            entry REAL,
            size REAL,
            note TEXT
        )
    """)
    conn.commit()
    conn.close()


def trades_today() -> int:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    d = datetime.utcnow().date().isoformat()
    c.execute("SELECT COUNT(*) FROM trades WHERE ts LIKE ?", (f"{d}%",))
    n = int(c.fetchone()[0] or 0)
    conn.close()
    return n


def log_trade(slug, market_id, side, entry, size, note):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "INSERT INTO trades (ts, slug, market_id, side, entry, size, note) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (datetime.utcnow().isoformat(), slug, market_id, side, entry, size, note),
    )
    conn.commit()
    conn.close()


def main():
    init_db()
    bankroll = STARTING_BANKROLL
    print("=" * 70)
    print("POLYMARKET BOT V2 (fresh architecture)")
    print("=" * 70)

    while True:
        try:
            tcount = trades_today()
            if tcount >= MAX_TRADES_PER_DAY:
                print(f"Cap reached: {tcount}/{MAX_TRADES_PER_DAY}. Monitoring...")
                time.sleep(LOOP_SECONDS)
                continue

            m = discover_current_round(SERIES_PREFIX, ROUND_MINUTES)
            if not m:
                print("No current round found yet. waiting...")
                time.sleep(LOOP_SECONDS)
                continue

            prob, why = get_prob_up()
            print(f"Round: {m.slug} | market_yes={m.yes_price:.3f} | {why}")
            if prob is None:
                time.sleep(LOOP_SECONDS)
                continue

            edge_yes = prob - m.yes_price
            edge_no = m.yes_price - prob

            side = None
            entry = None
            edge = 0.0
            if edge_yes >= MIN_EDGE:
                side = "BUY_YES"
                entry = m.yes_price
                edge = edge_yes
            elif edge_no >= MIN_EDGE:
                side = "BUY_NO"
                entry = 1.0 - m.yes_price
                edge = edge_no

            if side:
                risk_dollars = bankroll * RISK_PCT
                size = risk_dollars / max(entry, 1e-6)
                note = f"edge={edge:.4f}"
                log_trade(m.slug, m.market_id, side, entry, size, note)
                print(f"TRADE {side} | entry={entry:.4f} | size={size:.2f} | {note}")
            else:
                print(f"No trade | edge_yes={edge_yes:.4f} edge_no={edge_no:.4f}")

            time.sleep(LOOP_SECONDS)
        except KeyboardInterrupt:
            print("Stopping.")
            break
        except Exception as e:
            print(f"loop_error: {e}")
            time.sleep(LOOP_SECONDS)


if __name__ == "__main__":
    main()
