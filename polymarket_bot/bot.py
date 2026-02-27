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
from strategy import fair_probability, should_buy_yes, should_buy_no
from btc_signal import get_btc_signal_prob


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
BTC_ONLY = os.getenv("BTC_ONLY", "true").lower() == "true"
BTC_FOCUS_MODE = os.getenv("BTC_FOCUS_MODE", "ultrashort").lower()  # ultrashort|any
FORCE_MARKET_IDS = {x.strip() for x in os.getenv("FORCE_MARKET_IDS", "").split(",") if x.strip()}
FORCE_MARKET_SLUG_CONTAINS = os.getenv("FORCE_MARKET_SLUG_CONTAINS", "").strip().lower()
LOOP_SECONDS = _env_int("LOOP_SECONDS", 60)
DB_PATH = "trades.db"

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


def color_pnl(value: float) -> str:
    if value > 0:
        return f"{GREEN}${value:.2f}{RESET}"
    if value < 0:
        return f"{RED}-${abs(value):.2f}{RESET}"
    return f"${value:.2f}"


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
    cur.execute("SELECT market_id, side, price, size FROM trades WHERE side IN ('BUY_YES','BUY_NO')")
    rows = cur.fetchall()
    conn.close()

    pnl = 0.0
    for market_id, side, entry_price, size in rows:
        current_price = market_prices.get(str(market_id))
        if current_price is None:
            continue

        entry_price = float(entry_price)
        size = float(size)
        if side == "BUY_YES":
            pnl += (float(current_price) - entry_price) * size
        elif side == "BUY_NO":
            # NO contract value = 1 - YES price
            pnl += ((1.0 - float(current_price)) - (1.0 - entry_price)) * size
    return pnl


def is_ultrashort_btc_market(question_lower: str) -> bool:
    five_min_hint = ("5m" in question_lower) or ("5 min" in question_lower) or ("5-minute" in question_lower) or ("5 minute" in question_lower)
    updown_hint = ("up or down" in question_lower) or ("higher or lower" in question_lower)
    return five_min_hint and updown_hint


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

            btc_prob = None
            btc_reason = ""
            if BTC_ONLY:
                btc_prob, btc_reason = get_btc_signal_prob()
                print(f"BTC signal: {btc_reason}", flush=True)

            skip_forced_market = 0
            skip_non_btc = 0
            skip_signal_unavailable = 0
            skip_price = 0
            skip_edge = 0
            trades_placed_this_loop = 0

            for m in markets:
                if FORCE_MARKET_IDS and str(m.market_id) not in FORCE_MARKET_IDS:
                    skip_forced_market += 1
                    continue

                if FORCE_MARKET_SLUG_CONTAINS:
                    m_slug = (m.slug or "").lower()
                    if FORCE_MARKET_SLUG_CONTAINS not in m_slug:
                        skip_forced_market += 1
                        continue

                # Hard market-price filters to avoid tiny-price spam buys
                if m.yes_price < MIN_PRICE or m.yes_price > MAX_PRICE:
                    skip_price += 1
                    continue

                q_lower = m.question.lower()
                slug_lower = (m.slug or "").lower()
                is_btc_market = ("btc" in q_lower) or ("bitcoin" in q_lower) or ("btc" in slug_lower) or ("bitcoin" in slug_lower)

                if BTC_ONLY and not FORCE_MARKET_SLUG_CONTAINS and not is_btc_market:
                    skip_non_btc += 1
                    continue

                if BTC_ONLY and BTC_FOCUS_MODE == "ultrashort" and not FORCE_MARKET_SLUG_CONTAINS and not is_ultrashort_btc_market(q_lower):
                    skip_non_btc += 1
                    continue

                if BTC_ONLY:
                    if btc_prob is None:
                        skip_signal_unavailable += 1
                        continue
                    model_prob = fair_probability(btc_prob)
                else:
                    model_prob = fair_probability(m.signal_prob)

                buy_side = None
                edge_val = 0.0
                if should_buy_yes(m.yes_price, model_prob, MIN_EDGE):
                    buy_side = "BUY_YES"
                    edge_val = model_prob - m.yes_price
                elif should_buy_no(m.yes_price, model_prob, MIN_EDGE):
                    buy_side = "BUY_NO"
                    edge_val = m.yes_price - model_prob
                else:
                    skip_edge += 1

                if buy_side:
                    if already_traded_today(m.market_id, buy_side):
                        continue

                    # Recheck caps before each order
                    spent_today = today_trade_notional()
                    trade_count = trades_count_today()
                    if spent_today >= daily_cap or trade_count >= MAX_TRADES_PER_DAY:
                        print("In-loop cap reached. Stopping new trades this cycle.", flush=True)
                        break

                    # NO price is inverse of YES price
                    entry_price = m.yes_price if buy_side == "BUY_YES" else (1.0 - m.yes_price)
                    size = max_position_size(bankroll, entry_price)
                    if size <= 0:
                        continue

                    mode = "paper" if PAPER_MODE else "live"
                    note = f"edge={round(edge_val, 4)}"
                    log_trade(m.market_id, m.question, buy_side, entry_price, size, mode, note)
                    trades_placed_this_loop += 1
                    print(f"[{mode}] {buy_side} {m.market_id} @ {entry_price} size={size:.4f} {note}", flush=True)

            print(
                f"Loop debug | placed={trades_placed_this_loop} | skip_forced={skip_forced_market} | skip_non_btc={skip_non_btc} | skip_signal={skip_signal_unavailable} | skip_price={skip_price} | skip_edge={skip_edge}",
                flush=True,
            )

            trades_today = trades_count_today()
            notional_today = today_trade_notional()
            mtm = unrealized_pnl(market_prices)
            pnl_colored = color_pnl(mtm)
            print(
                f"Status | trades_today={trades_today}/{MAX_TRADES_PER_DAY} | notional_today=${notional_today:.2f} | unrealized_pnl={pnl_colored}",
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
