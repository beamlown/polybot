import os
import sqlite3
import sys
import time
from datetime import datetime, UTC

from dotenv import load_dotenv

from v4_discovery import discover
from v4_orderbook import OBReader
from v4_signal import signal_up_prob
from v4_errors import E_DB_INIT, E_DB_WRITE, E_CONFIG, fmt

load_dotenv()

STARTING_BANKROLL = float(os.getenv("STARTING_BANKROLL", "2000"))
SERIES_PREFIX = os.getenv("SERIES_PREFIX", "btc-updown")
ROUND_MINUTES = int(os.getenv("ROUND_MINUTES", "5"))
FORCE_SLUG = os.getenv("V4_FORCE_SLUG", "").strip()
AUTO_ROLL_FORCE_SLUG = os.getenv("AUTO_ROLL_FORCE_SLUG", "true").strip().lower() in ("1", "true", "yes", "on")
MIN_EDGE = float(os.getenv("MIN_EDGE", "0.05"))
MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", "5"))
MAX_ENTRIES_PER_ROUND = int(os.getenv("MAX_ENTRIES_PER_ROUND", "1"))
RISK_PCT = float(os.getenv("MAX_RISK_PER_TRADE_PCT", "0.005"))
MAX_SPREAD = float(os.getenv("MAX_SPREAD", "0.03"))
MIN_DEPTH_TOP5 = float(os.getenv("MIN_DEPTH_TOP5", "50"))
LOOP_SECONDS = int(os.getenv("LOOP_SECONDS", "5"))
DB = "trades_v4.db"
BUILD_TAG = "v4.2026-03-01.001"


def die(code: int, msg: str):
    print(fmt(code, msg))
    sys.exit(code)


def init_db():
    try:
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
    except Exception as e:
        die(E_DB_INIT, f"db init failed: {e}")


def trades_today() -> int:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    d = datetime.now(UTC).date().isoformat()
    c.execute("SELECT COUNT(*) FROM trades WHERE ts LIKE ?", (f"{d}%",))
    n = int(c.fetchone()[0] or 0)
    conn.close()
    return n


def entries_this_round(slug: str) -> int:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM trades WHERE slug = ?", (slug,))
    n = int(c.fetchone()[0] or 0)
    conn.close()
    return n


def log_trade(slug: str, market_id: str, side: str, entry: float, size: float, edge: float, note: str):
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute(
            "INSERT INTO trades (ts, slug, market_id, side, entry, size, edge, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now(UTC).isoformat(), slug, market_id, side, entry, size, edge, note),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        die(E_DB_WRITE, f"db write failed: {e}")


def seconds_to_next(slug: str, end_ts: int | None = None) -> int | None:
    try:
        # Use slug bucket timing for 5m rounds (Gamma endDate can point to series/event horizon).
        sfx = int(slug.rsplit("-", 1)[-1])
        return (sfx + ROUND_MINUTES * 60) - int(datetime.now(UTC).timestamp())
    except Exception:
        return None


def _advance_slug_once(slug: str) -> str:
    try:
        base, raw = slug.rsplit("-", 1)
        return f"{base}-{int(raw) + ROUND_MINUTES * 60}"
    except Exception:
        return slug


def main():
    if ROUND_MINUTES <= 0:
        die(E_CONFIG, "ROUND_MINUTES must be > 0")

    init_db()
    ob = OBReader()
    bankroll = STARTING_BANKROLL

    print("=" * 72)
    print(f"POLYMARKET BOT V4 (clean + debuggable) | {BUILD_TAG}")
    print("=" * 72)

    current_force_slug = FORCE_SLUG
    last_logged_slug = None

    while True:
        try:
            day_count = trades_today()
            if MAX_TRADES_PER_DAY > 0 and day_count >= MAX_TRADES_PER_DAY:
                print(f"No trade | daily cap {day_count}/{MAX_TRADES_PER_DAY}")
                time.sleep(LOOP_SECONDS)
                continue

            market, derr = discover(SERIES_PREFIX, ROUND_MINUTES, force_slug=current_force_slug or None)
            if derr:
                print(derr)
                # If a forced slug has expired or disappeared, optionally roll forward automatically.
                if current_force_slug and AUTO_ROLL_FORCE_SLUG and "[ERR 1103]" in derr:
                    nxt = _advance_slug_once(current_force_slug)
                    if nxt != current_force_slug:
                        current_force_slug = nxt
                        print(f"Auto-rolled forced slug -> {current_force_slug}")
                time.sleep(LOOP_SECONDS)
                continue
            if market is None:
                print("[ERR 1103] no current market")
                time.sleep(LOOP_SECONDS)
                continue

            if market.slug != last_logged_slug:
                print(
                    f"Market selected | slug={market.slug} | market_id={market.market_id} "
                    f"| yes_token_id={market.yes_token_id} | no_token_id={market.no_token_id}"
                )
                last_logged_slug = market.slug

            round_count = entries_this_round(market.slug)
            if round_count >= MAX_ENTRIES_PER_ROUND:
                eta = seconds_to_next(market.slug, market.end_ts)
                eta_safe = max(0, eta) if eta is not None else None
                eta_txt = f" | next in {eta_safe}s" if eta_safe is not None else ""
                print(f"Round: {market.slug} | No trade | round cap {round_count}/{MAX_ENTRIES_PER_ROUND}{eta_txt}")

                # If pinned slug is already expired, roll to next round automatically.
                if current_force_slug and AUTO_ROLL_FORCE_SLUG and eta is not None and eta < 0:
                    nxt = _advance_slug_once(current_force_slug)
                    if nxt != current_force_slug:
                        current_force_slug = nxt
                        print(f"Auto-rolled forced slug -> {current_force_slug}")

                time.sleep(LOOP_SECONDS)
                continue

            prob, stext, serr = signal_up_prob()
            if serr:
                print(serr)
                time.sleep(LOOP_SECONDS)
                continue

            book, berr = ob.read(market.yes_token_id)
            spread = None
            depth = 0.0
            imbalance = 0.0
            if berr:
                # Fallback to Gamma quoted spread/bid/ask when CLOB book is unavailable for token id.
                spread = market.gamma_spread
                if market.best_bid is not None and market.best_ask is not None:
                    depth = 9999.0  # treat as available quote depth proxy
                print(f"{berr} | fallback=gamma_quotes spread={spread} best_bid={market.best_bid} best_ask={market.best_ask}")
            else:
                spread = book.spread
                depth = book.depth_top5
                imbalance = book.imbalance

            print(
                f"Round: {market.slug} | yes={market.yes_price:.3f} | {stext} | spread={spread} | depth={depth:.1f} | imbalance={imbalance:.2f}"
            )

            if spread is not None and spread > MAX_SPREAD:
                print("No trade | spread too wide")
                time.sleep(LOOP_SECONDS)
                continue
            if depth < MIN_DEPTH_TOP5:
                print("No trade | depth too thin")
                time.sleep(LOOP_SECONDS)
                continue

            edge_yes = prob - market.yes_price
            edge_no = market.yes_price - prob

            side = None
            entry = None
            edge = 0.0
            if edge_yes >= MIN_EDGE:
                side = "BUY_YES"
                entry = market.yes_price
                edge = edge_yes
            elif edge_no >= MIN_EDGE:
                side = "BUY_NO"
                entry = market.no_price
                edge = edge_no

            if not side:
                print(f"No trade | edge_yes={edge_yes:.4f} edge_no={edge_no:.4f}")
                time.sleep(LOOP_SECONDS)
                continue

            risk = bankroll * RISK_PCT
            size = risk / max(entry, 1e-6)
            note = f"edge={edge:.4f} spread={spread} depth={depth:.1f} imbalance={imbalance:.2f}"
            log_trade(market.slug, market.market_id, side, entry, size, edge, note)
            print(f"TRADE {side} | entry={entry:.4f} | size={size:.2f} | {note}")

            time.sleep(LOOP_SECONDS)
        except KeyboardInterrupt:
            print("Stopping V4.")
            break
        except Exception as e:
            print(f"[ERR 1999] loop_error: {e}")
            time.sleep(LOOP_SECONDS)


if __name__ == "__main__":
    main()
