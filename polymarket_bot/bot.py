import os
import time
import sqlite3
from datetime import datetime, date
from dotenv import load_dotenv

from data_client import MarketClient
from strategy import fair_probability, should_buy_yes


load_dotenv()

PAPER_MODE = os.getenv("PAPER_MODE", "true").lower() == "true"
STARTING_BANKROLL = float(os.getenv("STARTING_BANKROLL", "200"))
MAX_RISK_PER_TRADE_PCT = float(os.getenv("MAX_RISK_PER_TRADE_PCT", "0.02"))
MAX_DAILY_DRAWDOWN_PCT = float(os.getenv("MAX_DAILY_DRAWDOWN_PCT", "0.10"))
MIN_EDGE = float(os.getenv("MIN_EDGE", "0.04"))
LOOP_SECONDS = int(os.getenv("LOOP_SECONDS", "60"))
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
        (datetime.utcnow().isoformat(), market_id, question, side, price, size, mode, note),
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


def max_position_size(bankroll: float, price: float) -> float:
    risk_dollars = bankroll * MAX_RISK_PER_TRADE_PCT
    if price <= 0:
        return 0.0
    return risk_dollars / price


def main():
    init_db()
    client = MarketClient()
    bankroll = STARTING_BANKROLL

    print(f"Bot started | PAPER_MODE={PAPER_MODE} | bankroll={bankroll}")

    while True:
        try:
            daily_cap = bankroll * MAX_DAILY_DRAWDOWN_PCT
            spent_today = today_trade_notional()
            if spent_today >= daily_cap:
                print("Daily risk cap reached. Sleeping...")
                time.sleep(LOOP_SECONDS)
                continue

            markets = client.fetch_markets()

            for m in markets:
                model_prob = fair_probability(m.signal_prob)
                if should_buy_yes(m.yes_price, model_prob, MIN_EDGE):
                    size = max_position_size(bankroll, m.yes_price)
                    if size <= 0:
                        continue

                    mode = "paper" if PAPER_MODE else "live"
                    note = f"edge={round(model_prob - m.yes_price, 4)}"
                    log_trade(m.market_id, m.question, "BUY_YES", m.yes_price, size, mode, note)
                    print(f"[{mode}] BUY_YES {m.market_id} @ {m.yes_price} size={size:.4f} {note}")

            time.sleep(LOOP_SECONDS)

        except KeyboardInterrupt:
            print("Stopping bot.")
            break
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(LOOP_SECONDS)


if __name__ == "__main__":
    main()
