import os
import sqlite3
import time
from datetime import datetime, UTC

from dotenv import load_dotenv

from v3_discovery import discover_latest_market
from v3_orderbook import OrderBookReader
from v3_signal import get_up_probability

load_dotenv()

STARTING_BANKROLL = float(os.getenv("STARTING_BANKROLL", "2000"))
SERIES_PREFIX = os.getenv("SERIES_PREFIX", "btc-updown")
ROUND_MINUTES = int(os.getenv("ROUND_MINUTES", "5"))
MIN_EDGE = float(os.getenv("MIN_EDGE", "0.05"))
MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", "5"))
MAX_ENTRIES_PER_ROUND = int(os.getenv("MAX_ENTRIES_PER_ROUND", "1"))
MAX_RISK_PER_TRADE_PCT = float(os.getenv("MAX_RISK_PER_TRADE_PCT", "0.005"))
MAX_SPREAD = float(os.getenv("MAX_SPREAD", "0.03"))
MIN_DEPTH_TOP5 = float(os.getenv("MIN_DEPTH_TOP5", "50"))
LOOP_SECONDS = int(os.getenv("LOOP_SECONDS", "5"))
DB = "trades_v3.db"


def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            slug TEXT,
            market_id TEXT,
            side TEXT,
            entry REAL,
            size REAL,
            edge REAL,
            note TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def trades_today() -> int:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    d = datetime.now(UTC).date().isoformat()
    c.execute("SELECT COUNT(*) FROM trades WHERE ts LIKE ?", (f"{d}%",))
    n = int(c.fetchone()[0] or 0)
    conn.close()
    return n


def entries_this_slug(slug: str) -> int:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM trades WHERE slug = ?", (slug,))
    n = int(c.fetchone()[0] or 0)
    conn.close()
    return n


def log_trade(slug: str, market_id: str, side: str, entry: float, size: float, edge: float, note: str):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "INSERT INTO trades (ts, slug, market_id, side, entry, size, edge, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (datetime.now(UTC).isoformat(), slug, market_id, side, entry, size, edge, note),
    )
    conn.commit()
    conn.close()


def _seconds_to_next_round(slug: str, round_minutes: int) -> int | None:
    try:
        start_ts = int(str(slug).rsplit("-", 1)[-1])
        end_ts = start_ts + (round_minutes * 60)
        return end_ts - int(datetime.now(UTC).timestamp())
    except Exception:
        return None


def main():
    init_db()
    ob = OrderBookReader()
    bankroll = STARTING_BANKROLL

    print("=" * 72)
    print("🚀 POLYMARKET BOT V3 (fresh market-discovery architecture)")
    print("=" * 72)

    while True:
        try:
            today_count = trades_today()
            if today_count >= MAX_TRADES_PER_DAY:
                print(f"Cap reached {today_count}/{MAX_TRADES_PER_DAY}. Monitoring...")
                time.sleep(LOOP_SECONDS)
                continue

            m = discover_latest_market(SERIES_PREFIX, ROUND_MINUTES)
            if not m:
                print("No matching round market visible yet. waiting...")
                time.sleep(LOOP_SECONDS)
                continue

            round_entries = entries_this_slug(m.slug)
            if round_entries >= MAX_ENTRIES_PER_ROUND:
                eta = _seconds_to_next_round(m.slug, ROUND_MINUTES)
                eta_txt = f" | next round in {eta}s" if eta is not None else ""
                print(f"Round: {m.slug} | No trade | round cap {round_entries}/{MAX_ENTRIES_PER_ROUND}{eta_txt}")
                time.sleep(LOOP_SECONDS)
                continue

            prob, signal_reason = get_up_probability()
            if prob is None:
                print(f"Round: {m.slug} | {signal_reason}")
                time.sleep(LOOP_SECONDS)
                continue

            book_token = m.yes_token_id if m.yes_token_id else m.no_token_id
            book = ob.stats(book_token) if book_token else None

            spread_ok = True
            depth_ok = True
            imbalance = 0.0
            spread_val = None
            depth_sum = 0.0
            if book:
                spread_val = book.spread
                imbalance = book.imbalance
                depth_sum = book.bid_depth_top5 + book.ask_depth_top5
                spread_ok = (spread_val is None) or (spread_val <= MAX_SPREAD)
                depth_ok = depth_sum >= MIN_DEPTH_TOP5

            edge_yes = prob - m.yes_price
            edge_no = m.yes_price - prob

            print(
                f"Round: {m.slug} | yes={m.yes_price:.3f} | {signal_reason} | spread={spread_val} | depth={depth_sum:.1f} | imbalance={imbalance:.2f}"
            )

            if not spread_ok:
                print("No trade | spread too wide")
                time.sleep(LOOP_SECONDS)
                continue
            if not depth_ok:
                print("No trade | depth too thin")
                time.sleep(LOOP_SECONDS)
                continue

            side = None
            entry = None
            edge = 0.0

            if edge_yes >= MIN_EDGE:
                side = "BUY_YES"
                entry = m.yes_price
                edge = edge_yes
            elif edge_no >= MIN_EDGE:
                side = "BUY_NO"
                entry = m.no_price
                edge = edge_no

            if not side:
                print(f"No trade | edge_yes={edge_yes:.4f} edge_no={edge_no:.4f}")
                time.sleep(LOOP_SECONDS)
                continue

            risk_dollars = bankroll * MAX_RISK_PER_TRADE_PCT
            size = risk_dollars / max(entry, 1e-6)

            note = f"edge={edge:.4f} spread={spread_val} depth={depth_sum:.1f} imbalance={imbalance:.2f}"
            log_trade(m.slug, m.market_id, side, entry, size, edge, note)
            print(f"TRADE {side} | entry={entry:.4f} | size={size:.2f} | {note}")

            time.sleep(LOOP_SECONDS)
        except KeyboardInterrupt:
            print("Stopping V3.")
            break
        except Exception as e:
            print(f"loop_error: {e}")
            time.sleep(LOOP_SECONDS)


if __name__ == "__main__":
    main()
