import os
import time
import sqlite3
from datetime import datetime, date, UTC

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False

from data_client import MarketClient
from strategy import fair_probability, should_buy_yes


load_dotenv()

def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


PAPER_MODE = os.getenv("PAPER_MODE", "true").lower() == "true"
STARTING_BANKROLL = _env_float("STARTING_BANKROLL", 200.0)
MAX_RISK_PER_TRADE_PCT = _env_float("MAX_RISK_PER_TRADE_PCT", 0.02)
MAX_DAILY_DRAWDOWN_PCT = _env_float("MAX_DAILY_DRAWDOWN_PCT", 0.10)
MAX_TRADES_PER_DAY = _env_int("MAX_TRADES_PER_DAY", 10)
MIN_EDGE = _env_float("MIN_EDGE", 0.04)
MIN_PRICE = _env_float("MIN_PRICE", 0.05)
MAX_PRICE = _env_float("MAX_PRICE", 0.85)
LOOP_SECONDS = _env_int("LOOP_SECONDS", 60)
DB_PATH = "trades.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            market_id TEXT NOT NULL,
            question TEXT NOT NULL,
            side TEXT NOT NULL,
            price REAL NOT NULL,
            size REAL NOT NULL,
            mode TEXT NOT NULL,
            note TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def log_trade(market_id: str, question: str, side: str, price: float, size: float, mode: str, note: str = ""):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO trades (ts, market_id, question, side, price, size, mode, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (datetime.now(UTC).isoformat(), market_id, question, side, price, size, mode, note),
    )
    conn.commit()
    conn.close()


def today_trade_notional() -> float:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    today = date.today().isoformat()
    cur.execute("SELECT COALESCE(SUM(price * size), 0) FROM trades WHERE ts LIKE ?", (f"{today}%",))
    val = float(cur.fetchone()[0] or 0)
    conn.close()
    return val


def already_traded_today(market_id: str, side: str = "BUY_YES") -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    today = date.today().isoformat()
    cur.execute(
        "SELECT 1 FROM trades WHERE market_id = ? AND side = ? AND ts LIKE ? LIMIT 1",
        (market_id, side, f"{today}%"),
    )
    row = cur.fetchone()
    conn.close()
    return row is not None


def trades_count_today() -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    today = date.today().isoformat()
    cur.execute("SELECT COUNT(*) FROM trades WHERE ts LIKE ?", (f"{today}%",))
    val = int(cur.fetchone()[0] or 0)
    conn.close()
    return val


def max_position_size(bankroll: float, price: float) -> float:
    risk_dollars = bankroll * MAX_RISK_PER_TRADE_PCT
    if price <= 0:
        return 0.0
    return risk_dollars / price


def unrealized_pnl(market_prices: dict[str, float]) -> float:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT market_id, price, size FROM trades WHERE side = 'BUY_YES'")
    rows = cur.fetchall()
    conn.close()

    pnl = 0.0
    for market_id, entry_price, size in rows:
        current_price = market_prices.get(str(market_id))
        if current_price is None:
            continue
        pnl += (float(current_price) - float(entry_price)) * float(size)
    return pnl


def main():
    init_db()
    client = MarketClient()
    bankroll = STARTING_BANKROLL

    print(f"Bot started | PAPER_MODE={PAPER_MODE} | bankroll={bankroll}", flush=True)

    while True:
        try:
            daily_cap = bankroll * MAX_DAILY_DRAWDOWN_PCT
            spent_today = today_trade_notional()
            trade_count = trades_count_today()

            if spent_today >= daily_cap:
                print("Daily risk cap reached. Sleeping...", flush=True)
                time.sleep(LOOP_SECONDS)
                continue

            if trade_count >= MAX_TRADES_PER_DAY:
                print("Daily trade-count cap reached. Sleeping...", flush=True)
                time.sleep(LOOP_SECONDS)
                continue

            markets = client.fetch_markets()
            print(f"Fetched {len(markets)} active markets", flush=True)
            market_prices = {str(m.market_id): float(m.yes_price) for m in markets}

            for m in markets:
                # Hard market-price filters to avoid tiny-price spam buys
                if m.yes_price < MIN_PRICE or m.yes_price > MAX_PRICE:
                    continue

                model_prob = fair_probability(m.signal_prob)
                if should_buy_yes(m.yes_price, model_prob, MIN_EDGE):
                    if already_traded_today(m.market_id, "BUY_YES"):
                        continue

                    # Recheck caps before each order
                    spent_today = today_trade_notional()
                    trade_count = trades_count_today()
                    if spent_today >= daily_cap or trade_count >= MAX_TRADES_PER_DAY:
                        print("In-loop cap reached. Stopping new trades this cycle.", flush=True)
                        break

                    size = max_position_size(bankroll, m.yes_price)
                    if size <= 0:
                        continue

                    mode = "paper" if PAPER_MODE else "live"
                    note = f"edge={round(model_prob - m.yes_price, 4)}"
                    log_trade(m.market_id, m.question, "BUY_YES", m.yes_price, size, mode, note)
                    print(f"[{mode}] BUY_YES {m.market_id} @ {m.yes_price} size={size:.4f} {note}", flush=True)

            trades_today = trades_count_today()
            notional_today = today_trade_notional()
            mtm = unrealized_pnl(market_prices)
            print(
                f"Status | trades_today={trades_today}/{MAX_TRADES_PER_DAY} | notional_today=${notional_today:.2f} | unrealized_pnl=${mtm:.2f}",
                flush=True,
            )

            time.sleep(LOOP_SECONDS)

        except KeyboardInterrupt:
            print("Stopping bot.")
            break
        except Exception as e:
            print(f"Loop error: {e}", flush=True)
            time.sleep(LOOP_SECONDS)


if __name__ == "__main__":
    main()
