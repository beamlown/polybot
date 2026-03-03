import json
import os
import random
import re
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
SERIES_PREFIXES = [x.strip() for x in os.getenv("SERIES_PREFIXES", SERIES_PREFIX).split(",") if x.strip()]
ROUND_MINUTES = int(os.getenv("ROUND_MINUTES", "5"))
MAX_CONCURRENT_TRADES = int(os.getenv("MAX_CONCURRENT_TRADES", "2"))
MIN_TOP_BOOK_USD = float(os.getenv("MIN_TOP_BOOK_USD", "15"))
TOP_BOOK_STRONG_USD = float(os.getenv("TOP_BOOK_STRONG_USD", "50"))
MIN_VOLUME24H = float(os.getenv("MIN_VOLUME24H", "5000"))
FORCE_SLUG = os.getenv("V4_FORCE_SLUG", "").strip()
AUTO_ROLL_FORCE_SLUG = os.getenv("AUTO_ROLL_FORCE_SLUG", "true").strip().lower() in ("1", "true", "yes", "on")
MIN_EDGE = float(os.getenv("MIN_EDGE", "0.05"))
AUTO_TAKE_PROFIT_PCT = float(os.getenv("AUTO_TAKE_PROFIT_PCT", "0"))
AUTO_TAKE_PROFIT_ABS = float(os.getenv("AUTO_TAKE_PROFIT_ABS", "0.65"))
PARTIAL_TP_TRIGGER_PCT = float(os.getenv("PARTIAL_TP_TRIGGER_PCT", "0.30"))
PARTIAL_TP_SELL_FRACTION = float(os.getenv("PARTIAL_TP_SELL_FRACTION", "0.25"))
TP_PRINCIPAL_TRIGGER_PCT = float(os.getenv("TP_PRINCIPAL_TRIGGER_PCT", "0.22"))
TP_PRINCIPAL_SELL_FRAC = float(os.getenv("TP_PRINCIPAL_SELL_FRAC", "0.70"))
RUNNER_STOP_BUFFER_PCT = float(os.getenv("RUNNER_STOP_BUFFER_PCT", "0.02"))
RUNNER_EXPIRY_CLOSE_SEC = int(os.getenv("RUNNER_EXPIRY_CLOSE_SEC", "20"))
GROUP_TAKE_PROFIT_PCT = float(os.getenv("GROUP_TAKE_PROFIT_PCT", "0.30"))
BREAKEVEN_AFTER_PARTIAL = os.getenv("BREAKEVEN_AFTER_PARTIAL", "true").strip().lower() in ("1", "true", "yes", "on")
BREAKEVEN_BUFFER_PCT = float(os.getenv("BREAKEVEN_BUFFER_PCT", "0.01"))
AUTO_STOP_LOSS_PCT = float(os.getenv("AUTO_STOP_LOSS_PCT", "0"))
MAX_STOP_PCT = float(os.getenv("MAX_STOP_PCT", "0.30"))
TRAILING_STOP_AFTER_PARTIAL_PCT = float(os.getenv("TRAILING_STOP_AFTER_PARTIAL_PCT", "0.08"))
TIME_STOP_SECONDS = int(os.getenv("TIME_STOP_SECONDS", "120"))
TIME_STOP_MAX_PNL_PCT = float(os.getenv("TIME_STOP_MAX_PNL_PCT", "0.02"))
STOP_LOSS_FINAL_MINUTE_ONLY = os.getenv("STOP_LOSS_FINAL_MINUTE_ONLY", "true").strip().lower() in ("1", "true", "yes", "on")
MAX_QUOTE_MISMATCH = float(os.getenv("MAX_QUOTE_MISMATCH", "0.12"))
STOPLOSS_REENTRY_COOLDOWN_SECONDS = int(os.getenv("STOPLOSS_REENTRY_COOLDOWN_SECONDS", "45"))
STOP_LOSS_ARMING_DELAY_SECONDS = int(os.getenv("STOP_LOSS_ARMING_DELAY_SECONDS", "15"))
STOP_LOSS_ARMING_DELAY_SECONDS_SL = int(os.getenv("STOP_LOSS_ARMING_DELAY_SECONDS_SL", "0"))
PENDING_ORDER_TIMEOUT_SEC = int(os.getenv("PENDING_ORDER_TIMEOUT_SEC", "15"))
MAX_HOLD_SECONDS = int(os.getenv("MAX_HOLD_SECONDS", "300"))
SAME_SIDE_ENTRY_COOLDOWN_SECONDS = int(os.getenv("SAME_SIDE_ENTRY_COOLDOWN_SECONDS", "20"))
MIN_REENTRY_PRICE_IMPROVEMENT = float(os.getenv("MIN_REENTRY_PRICE_IMPROVEMENT", "0.01"))
STRONG_REGIME_ONLY = os.getenv("STRONG_REGIME_ONLY", "true").strip().lower() in ("1", "true", "yes", "on")
BULL_MIN_VOTES = int(os.getenv("BULL_MIN_VOTES", "4"))
BEAR_MAX_VOTES = int(os.getenv("BEAR_MAX_VOTES", "1"))
MIN_PROB_DISTANCE = float(os.getenv("MIN_PROB_DISTANCE", "0.06"))
FAIR_VALUE_DISCOUNT_PCT = float(os.getenv("FAIR_VALUE_DISCOUNT_PCT", "0.03"))
MIN_SIDE_ADVANTAGE = float(os.getenv("MIN_SIDE_ADVANTAGE", "0.02"))
MAX_SAME_SIDE_OPEN_PER_ROUND = int(os.getenv("MAX_SAME_SIDE_OPEN_PER_ROUND", "2"))
SIDE_PERF_LOOKBACK = int(os.getenv("SIDE_PERF_LOOKBACK", "30"))
LOSING_SIDE_EDGE_PENALTY = float(os.getenv("LOSING_SIDE_EDGE_PENALTY", "0.03"))
ENTRY_PRICE_FLOOR = float(os.getenv("ENTRY_PRICE_FLOOR", "0.08"))
ENTRY_PRICE_CEIL = float(os.getenv("ENTRY_PRICE_CEIL", "0.92"))
BUY_NO_MIN_ENTRY = float(os.getenv("BUY_NO_MIN_ENTRY", "0.30"))
BUY_NO_MAX_ENTRY = float(os.getenv("BUY_NO_MAX_ENTRY", "0.40"))
BUY_YES_MIN_ENTRY = float(os.getenv("BUY_YES_MIN_ENTRY", "0.40"))
BUY_YES_MAX_ENTRY = float(os.getenv("BUY_YES_MAX_ENTRY", "0.60"))
HIGH_CONVICTION_MULTIPLIER = float(os.getenv("HIGH_CONVICTION_MULTIPLIER", "3.0"))
HIGH_CONV_MIN_EDGE = float(os.getenv("HIGH_CONV_MIN_EDGE", "0.22"))
HIGH_CONV_MIN_PROB = float(os.getenv("HIGH_CONV_MIN_PROB", "0.72"))
HIGH_CONV_MIN_VOTES = int(os.getenv("HIGH_CONV_MIN_VOTES", "6"))
MIXED_PROBE_ENABLED = os.getenv("MIXED_PROBE_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")
MIXED_RISK_MULT = float(os.getenv("MIXED_RISK_MULT", "0.35"))
MAX_RSI_FOR_LONG = float(os.getenv("MAX_RSI_FOR_LONG", "72"))
LATE_WINDOW_START_SECONDS = int(os.getenv("LATE_WINDOW_START_SECONDS", "250"))
LATE_WINDOW_RISK_MULT = float(os.getenv("LATE_WINDOW_RISK_MULT", "0.5"))
MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", "5"))
MAX_ENTRIES_PER_ROUND = int(os.getenv("MAX_ENTRIES_PER_ROUND", "1"))
MAX_TRADES_PER_SLUG = int(os.getenv("MAX_TRADES_PER_SLUG", "1"))
RISK_PCT = float(os.getenv("MAX_RISK_PER_TRADE_PCT", "0.005"))
MAX_SPREAD = float(os.getenv("MAX_SPREAD", "0.03"))
MIN_DEPTH_TOP5 = float(os.getenv("MIN_DEPTH_TOP5", "50"))
MIN_DEPTH_TOP5_USD = float(os.getenv("MIN_DEPTH_TOP5_USD", "50"))
EST_TAKER_FEE_RATE = float(os.getenv("EST_TAKER_FEE_RATE", "0.0025"))
EST_TAKER_FEE_EXP = float(os.getenv("EST_TAKER_FEE_EXP", "2.0"))
NET_EDGE_BUFFER = float(os.getenv("NET_EDGE_BUFFER", "0.005"))
LOOP_SECONDS = int(os.getenv("LOOP_SECONDS", "5"))
QUIET_LOGGING = os.getenv("QUIET_LOGGING", "true").strip().lower() in ("1", "true", "yes", "on")
MIN_SECONDS_TO_EXPIRY = int(os.getenv("MIN_SECONDS_TO_EXPIRY", "0"))
ENTRY_WINDOW_START_SECONDS = int(os.getenv("ENTRY_WINDOW_START_SECONDS", "0"))
ENTRY_WINDOW_END_SECONDS = int(os.getenv("ENTRY_WINDOW_END_SECONDS", "999999"))
MAX_EXIT_QUOTE_AGE_SECONDS = float(os.getenv("MAX_EXIT_QUOTE_AGE_SECONDS", "2.0"))
FORCE_FLAT_BEFORE_EXPIRY_SECONDS = int(os.getenv("FORCE_FLAT_BEFORE_EXPIRY_SECONDS", "10"))
SCALE_IN_ENABLED = os.getenv("SCALE_IN_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")
MAX_SCALE_INS_PER_GROUP = int(os.getenv("MAX_SCALE_INS_PER_GROUP", "2"))
SCALE_IN_MIN_IMPROVEMENT = float(os.getenv("SCALE_IN_MIN_IMPROVEMENT", "0.02"))
DB = "trades_v4.db"
BUILD_TAG = "v5.4.2026-03-02.001"
ENGINE_TAG = "v5_stop_enforcement"
STATE_PATH = os.path.join(os.path.dirname(__file__), "runtime", "state_v5.json")
_last_state_write: float = 0.0
STATE_WRITE_INTERVAL_SEC: float = float(os.getenv("STATE_WRITE_INTERVAL_SEC", "2.0"))


def die(code: int, msg: str):
    print(fmt(code, msg))
    sys.exit(code)


def vprint(msg: str):
    if not QUIET_LOGGING:
        print(msg)


def parse_ts(raw: str) -> datetime:
    """Safely parse ISO timestamp, always returning a UTC-aware datetime."""
    s = str(raw).strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def simulate_exit_fill(trigger_bid: float, spread: float | None = None, top_book_usd: float | None = None, tick: float = 0.01):
    s = spread if (spread is not None and spread > 0) else 0.01
    tbu = top_book_usd if (top_book_usd is not None and top_book_usd > 0) else 25.0
    if tbu >= 50 and s <= 0.01:
        delay_ms = random.randint(200, 600)
        retries = 0
    else:
        delay_ms = random.randint(800, 2000)
        retries = random.randint(0, 2)
    # Paper realism guard: allow at most 1 tick adverse slip from trigger; retries add delay, not runaway price decay.
    fill_price = max(0.0, trigger_bid - tick)
    slippage_ticks = (fill_price - trigger_bid) / tick if tick > 0 else 0.0
    return fill_price, delay_ms, retries, slippage_ticks


def is_stale_quote(quote_ts: datetime | None) -> bool:
    if quote_ts is None:
        return False
    try:
        age = (datetime.now(UTC) - quote_ts).total_seconds()
        return age > MAX_EXIT_QUOTE_AGE_SECONDS
    except Exception:
        return False


def quote_mark_for_open(slug: str, side: str, ob: OBReader | None = None) -> float | None:
    try:
        pref = _series_prefix_from_slug(str(slug))
        market, derr = discover(pref, ROUND_MINUTES, force_slug=str(slug))
        if derr or market is None:
            return None

        if side == "BUY_YES":
            if ob is not None and market.yes_token_id:
                b, e = ob.read(market.yes_token_id)
                if e is None and b is not None and b.best_bid is not None:
                    return float(b.best_bid)
            return float(market.yes_price) if market.yes_price is not None else None

        if side == "BUY_NO":
            if ob is not None and market.no_token_id:
                b, e = ob.read(market.no_token_id)
                if e is None and b is not None and b.best_bid is not None:
                    return float(b.best_bid)
            if market.yes_price is not None:
                return max(0.0, min(1.0, 1.0 - float(market.yes_price)))
            return None
    except Exception:
        return None
    return None


def unrealized_pnl_estimate(ob: OBReader | None = None) -> float:
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        rows = c.execute(
            """
            SELECT slug, side, entry, COALESCE(remaining_size,size) AS rem
            FROM trades
            WHERE closed_ts IS NULL AND COALESCE(remaining_size,size)>0
            """
        ).fetchall()
        conn.close()
        if not rows:
            return 0.0

        by_slug = {}
        for slug, side, entry, rem in rows:
            by_slug.setdefault(str(slug), []).append((str(side), float(entry), float(rem)))

        total = 0.0
        ob = ob or OBReader()
        for slug, legs in by_slug.items():
            for side, entry, rem in legs:
                mark = quote_mark_for_open(slug, side, ob)
                if mark is None:
                    continue
                total += (float(mark) - entry) * rem
        return float(total)
    except Exception:
        return 0.0


def write_state(status_line: str = "", ob: OBReader | None = None):
    global _last_state_write
    now_mono = time.monotonic()
    if now_mono - _last_state_write < STATE_WRITE_INTERVAL_SEC:
        return
    _last_state_write = now_mono
    try:
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        total = int(c.execute("SELECT COUNT(*) FROM trades").fetchone()[0] or 0)
        open_n = int(c.execute("SELECT COUNT(*) FROM trades WHERE closed_ts IS NULL AND COALESCE(remaining_size,size)>0").fetchone()[0] or 0)
        realized = float(c.execute("SELECT COALESCE(SUM(realized_pnl),0) FROM trades WHERE closed_ts IS NOT NULL").fetchone()[0] or 0.0)
        unrealized = unrealized_pnl_estimate(ob=ob)
        start_bal = STARTING_BANKROLL
        bal = start_bal + realized
        live_bal = start_bal + realized + unrealized
        open_rows = c.execute("SELECT id,slug,side,entry,COALESCE(remaining_size,size) FROM trades WHERE closed_ts IS NULL AND COALESCE(remaining_size,size)>0 ORDER BY id DESC LIMIT 8").fetchall()

        open_with_pnl = []
        ob_live = ob or OBReader()
        for rid, rslug, rside, rentry, rrem in open_rows:
            mark = quote_mark_for_open(str(rslug), str(rside), ob_live)
            rpnl = ((float(mark) - float(rentry)) * float(rrem)) if mark is not None else None
            open_with_pnl.append((rid, rslug, rside, float(rentry), float(rrem), mark, rpnl))
        recent = c.execute("SELECT id,slug,side,COALESCE(close_note,'n/a'),COALESCE(realized_pnl,0), COALESCE(entry,0), COALESCE(close_price, entry) FROM trades WHERE closed_ts IS NOT NULL ORDER BY id DESC LIMIT 10").fetchall()

        def rolling(n: int):
            rows = c.execute("SELECT COALESCE(realized_pnl,0) FROM trades WHERE closed_ts IS NOT NULL ORDER BY id DESC LIMIT ?", (int(n),)).fetchall()
            vals = [float(r[0] or 0.0) for r in rows]
            w = sum(1 for v in vals if v > 0)
            l = sum(1 for v in vals if v < 0)
            b = sum(1 for v in vals if abs(v) < 1e-12)
            d = w + l
            wr = (w / d * 100.0) if d > 0 else 0.0
            return {"n": len(vals), "wins": w, "losses": l, "breakeven": b, "wr": wr, "pnl": sum(vals)}

        roll = {"r25": rolling(25), "r50": rolling(50), "r100": rolling(100)}
        conn.close()
        payload = {
            "engine": ENGINE_TAG,
            "build": BUILD_TAG,
            "now": datetime.now(UTC).isoformat(),
            "balance_est": bal,
            "live_balance_est": live_bal,
            "start_balance": start_bal,
            "pnl": {"realized_all": realized, "unrealized": unrealized, "net": realized + unrealized},
            "slots": {"open": open_n, "pending": 0, "max": MAX_CONCURRENT_TRADES},
            "open_positions": [
                {"id":r[0],"slug":r[1],"side":r[2],"entry":r[3],"remaining_size":r[4],"mark":r[5],"pnl_usd":r[6]}
                for r in open_with_pnl
            ],
            "recent_closed": [
                {"id":r[0],"slug":r[1],"side":r[2],"reason":r[3],"pnl_usd":r[4],"entry":r[5],"close":r[6]}
                for r in recent
            ],
            "total_trades": total,
            "rolling": roll,
            "status_line": status_line,
        }
        tmp = STATE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, STATE_PATH)
    except Exception:
        pass


def init_db():
    try:
        conn = sqlite3.connect(DB)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
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

        cols = [r[1] for r in c.execute("PRAGMA table_info(trades)").fetchall()]
        if "trade_token_id" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN trade_token_id TEXT")
        if "entry_source" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN entry_source TEXT")
        if "closed_ts" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN closed_ts TEXT")
        if "close_price" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN close_price REAL")
        if "close_note" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN close_note TEXT")
        if "realized_pnl" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN realized_pnl REAL")
        if "remaining_size" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN remaining_size REAL")
            c.execute("UPDATE trades SET remaining_size = size WHERE remaining_size IS NULL")
        if "partial_tp_done" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN partial_tp_done INTEGER DEFAULT 0")
        if "exit_trigger_price" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN exit_trigger_price REAL")
        if "exit_fill_price" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN exit_fill_price REAL")
        if "slippage_ticks" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN slippage_ticks REAL")
        if "fill_delay_ms" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN fill_delay_ms INTEGER")
        if "fill_retries" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN fill_retries INTEGER")
        if "peak_price" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN peak_price REAL")
        if "avg_entry" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN avg_entry REAL")
        if "scale_in_count" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN scale_in_count INTEGER DEFAULT 0")
        if "parent_trade_id" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN parent_trade_id INTEGER")
        if "entry_tier" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN entry_tier INTEGER DEFAULT 1")
        if "is_scale_in" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN is_scale_in INTEGER DEFAULT 0")
        if "scale_group_id" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN scale_group_id TEXT")
        if "scale_trigger_note" not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN scale_trigger_note TEXT")

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_intents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT,
                slug TEXT,
                side TEXT,
                status TEXT,
                expires_ts TEXT
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


def trades_taken_on_slug(slug: str) -> int:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    n = int(c.execute("SELECT COUNT(*) FROM trades WHERE slug = ?", (slug,)).fetchone()[0] or 0)
    conn.close()
    return n


def open_positions_total() -> int:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    q = "SELECT COUNT(*) FROM trades WHERE closed_ts IS NULL AND COALESCE(remaining_size,size)>0"
    n = int(c.execute(q).fetchone()[0] or 0)
    conn.close()
    return n


def pending_intents_total() -> int:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    n = int(c.execute("SELECT COUNT(*) FROM pending_intents WHERE status='PENDING'").fetchone()[0] or 0)
    conn.close()
    return n


def cleanup_expired_intents() -> int:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    now_iso = datetime.now(UTC).isoformat()
    c.execute("UPDATE pending_intents SET status='EXPIRED' WHERE status='PENDING' AND expires_ts IS NOT NULL AND expires_ts < ?", (now_iso,))
    n = int(c.rowcount or 0)
    conn.commit()
    conn.close()
    return n


def has_pending_intent(slug: str, side: str) -> bool:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    n = int(c.execute("SELECT COUNT(*) FROM pending_intents WHERE slug=? AND side=? AND status='PENDING'", (slug, side)).fetchone()[0] or 0)
    conn.close()
    return n > 0


def reserve_intent(slug: str, side: str) -> int:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if int(c.execute("SELECT COUNT(*) FROM pending_intents WHERE slug=? AND side=? AND status='PENDING'", (slug, side)).fetchone()[0] or 0) > 0:
        conn.close()
        return 0
    now = datetime.now(UTC)
    expires = now.timestamp() + max(1, PENDING_ORDER_TIMEOUT_SEC)
    c.execute("INSERT INTO pending_intents (ts,slug,side,status,expires_ts) VALUES (?,?,?,?,?)", (now.isoformat(), slug, side, 'PENDING', datetime.fromtimestamp(expires, UTC).isoformat()))
    rid = int(c.lastrowid or 0)
    conn.commit()
    conn.close()
    return rid


def resolve_intent(intent_id: int, status: str = "DONE"):
    if intent_id <= 0:
        return
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE pending_intents SET status=? WHERE id=?", (status, int(intent_id)))
    conn.commit()
    conn.close()


def open_positions_this_round(slug: str) -> int:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM trades WHERE slug = ? AND closed_ts IS NULL AND COALESCE(remaining_size, size) > 0", (slug,))
    n = int(c.fetchone()[0] or 0)
    conn.close()
    return n


def log_trade(slug: str, market_id: str, side: str, entry: float, size: float, edge: float, note: str, trade_token_id: str | None, entry_source: str,
              parent_trade_id: int | None = None, entry_tier: int = 1, is_scale_in: int = 0,
              scale_group_id: str | None = None, scale_trigger_note: str | None = None, scale_in_count: int = 0):
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute(
            "INSERT INTO trades (ts, slug, market_id, side, entry, size, edge, note, trade_token_id, entry_source, remaining_size, partial_tp_done, peak_price, avg_entry, scale_in_count, parent_trade_id, entry_tier, is_scale_in, scale_group_id, scale_trigger_note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now(UTC).isoformat(), slug, market_id, side, entry, size, edge, note, trade_token_id, entry_source, size, 0, entry, entry, int(scale_in_count), parent_trade_id, int(entry_tier), int(is_scale_in), scale_group_id, scale_trigger_note),
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


def realized_net_pnl() -> float:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    cols = [r[1] for r in c.execute("PRAGMA table_info(trades)").fetchall()]
    if "realized_pnl" not in cols:
        conn.close()
        return 0.0
    val = c.execute("SELECT COALESCE(SUM(realized_pnl), 0.0) FROM trades").fetchone()[0]
    conn.close()
    try:
        return float(val)
    except Exception:
        return 0.0


def current_balance_realized_only() -> float:
    return max(0.0, STARTING_BANKROLL + realized_net_pnl())


def maybe_auto_take_profit(slug: str, sell_yes_px: float | None, sell_no_px: float | None, quote_ts: datetime | None = None) -> int:
    if AUTO_TAKE_PROFIT_PCT <= 0:
        return 0
    if is_stale_quote(quote_ts):
        print(f"STALE_QUOTE_SKIP | action=take_profit | slug={slug}")
        return 0
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    rows = c.execute(
        """
        SELECT id, side, entry, size, COALESCE(remaining_size, size) AS rem, COALESCE(partial_tp_done, 0) AS ptd
        FROM trades
        WHERE slug = ? AND closed_ts IS NULL AND COALESCE(remaining_size, size) > 0
        ORDER BY id ASC
        """,
        (slug,),
    ).fetchall()

    closed = 0
    now_iso = datetime.now(UTC).isoformat()
    for tid, side, entry, size, rem, ptd in rows:
        entry = float(entry)
        rem = float(rem)

        close_price = sell_yes_px if side == "BUY_YES" else sell_no_px
        if close_price is None:
            continue

        # 1) Deterministic principal recovery partial
        partial_target = entry * (1.0 + TP_PRINCIPAL_TRIGGER_PCT)
        if int(ptd) == 0 and close_price >= partial_target:
            qty = max(0.0, rem * max(0.0, min(1.0, TP_PRINCIPAL_SELL_FRAC)))
            if qty > 0:
                pnl_partial = (float(close_price) - entry) * qty
                rem_after = max(0.0, rem - qty)
                c.execute(
                    "UPDATE trades SET remaining_size = ?, partial_tp_done = 1, close_note = ?, realized_pnl = COALESCE(realized_pnl, 0) + ? WHERE id = ?",
                    (rem_after, "runner_partial_take_profit", float(pnl_partial), int(tid)),
                )
                side_txt = "UP" if side == "BUY_YES" else "DOWN"
                runner_stop = entry * (1.0 + RUNNER_STOP_BUFFER_PCT)
                print(f"TP_PARTIAL | id={tid} token={side_txt} trigger={close_price:.4f} sold_frac={TP_PRINCIPAL_SELL_FRAC:.2f} sold={qty:.2f}/{rem:.2f} pnl={pnl_partial:+.2f}")
                print(f"RUNNER_ARMED | id={tid} new_stop={runner_stop:.4f} rem={rem_after:.2f}")
                rem = rem_after

        # 2) Full close remainder at standard TP or absolute price target.
        tp_target = entry * (1.0 + AUTO_TAKE_PROFIT_PCT)
        abs_target_hit = (AUTO_TAKE_PROFIT_ABS > 0 and close_price >= AUTO_TAKE_PROFIT_ABS)
        if rem > 0 and (close_price >= tp_target or abs_target_hit):
            trigger = float(close_price)
            fill, delay_ms, retries, slip_ticks = simulate_exit_fill(trigger, spread=0.01, top_book_usd=50.0)
            pnl = (fill - entry) * rem
            c.execute(
                "UPDATE trades SET closed_ts = ?, close_price = ?, close_note = ?, realized_pnl = COALESCE(realized_pnl, 0) + ?, remaining_size = 0, exit_trigger_price = ?, exit_fill_price = ?, slippage_ticks = ?, fill_delay_ms = ?, fill_retries = ? WHERE id = ?",
                (now_iso, float(fill), "auto_take_profit", float(pnl), trigger, float(fill), float(slip_ticks), int(delay_ms), int(retries), int(tid)),
            )
            closed += 1
            side_txt = "UP" if side == "BUY_YES" else "DOWN"
            print(f"EXIT_TRIGGER | id={tid} token={side_txt} mark_bid={trigger:.4f} tp_hit=True sl_hit=False quote_age=0.0s")
            print(f"EXIT_ORDER | id={tid} type=SELL limit={max(0.0, trigger-0.01):.4f} attempt=1")
            print(f"EXIT_FILLED | id={tid} fill={fill:.4f} slippage={slip_ticks:+.1f}t ttf={delay_ms}ms retries={retries}")
            print(f"SELL TP | {side_txt} | id={tid} | pnl={pnl:+.2f}")

    conn.commit()
    conn.close()
    return closed


def has_recent_stoploss(slug: str) -> bool:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    row = c.execute(
        """
        SELECT closed_ts
        FROM trades
        WHERE slug = ? AND close_note = 'auto_stop_loss'
        ORDER BY id DESC
        LIMIT 1
        """,
        (slug,),
    ).fetchone()
    conn.close()
    if not row or not row[0]:
        return False
    try:
        ts = parse_ts(row[0])
        age = (datetime.now(UTC) - ts).total_seconds()
        return age < STOPLOSS_REENTRY_COOLDOWN_SECONDS
    except Exception:
        return False


def parse_regime_votes(signal_text: str) -> tuple[str | None, int | None]:
    regime = None
    votes = None
    try:
        txt = str(signal_text or "")
        m_reg = re.search(r"regime\s*=\s*([A-Za-z_]+)", txt, flags=re.IGNORECASE)
        if m_reg:
            regime = m_reg.group(1).strip().upper()

        m_votes = re.search(r"votes\s*=\s*(\d+)", txt, flags=re.IGNORECASE)
        if m_votes:
            votes = int(m_votes.group(1))
    except Exception:
        return regime, votes
    return regime, votes


def has_open_opposite_side(slug: str, side: str) -> bool:
    opposite = "BUY_NO" if side == "BUY_YES" else "BUY_YES"
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    q = "SELECT COUNT(*) FROM trades WHERE slug=? AND side=? AND closed_ts IS NULL AND COALESCE(remaining_size,size)>0"
    n = int(c.execute(q, (slug, opposite)).fetchone()[0] or 0)
    conn.close()
    return n > 0


def open_same_side_count(slug: str, side: str) -> int:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    q = "SELECT COUNT(*) FROM trades WHERE slug=? AND side=? AND closed_ts IS NULL AND COALESCE(remaining_size,size)>0"
    n = int(c.execute(q, (slug, side)).fetchone()[0] or 0)
    conn.close()
    return n


def recent_side_realized_pnl(side: str, lookback: int) -> float:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    cols = [r[1] for r in c.execute("PRAGMA table_info(trades)").fetchall()]
    if "realized_pnl" not in cols or "closed_ts" not in cols:
        conn.close()
        return 0.0
    rows = c.execute(
        "SELECT COALESCE(realized_pnl,0) FROM trades WHERE side=? AND closed_ts IS NOT NULL ORDER BY id DESC LIMIT ?",
        (side, max(1, lookback)),
    ).fetchall()
    conn.close()
    return float(sum(float(r[0] or 0) for r in rows))


def estimated_taker_fee_per_share(price: float) -> float:
    p = max(0.0, min(1.0, float(price)))
    return EST_TAKER_FEE_RATE * (min(p, 1.0 - p) ** EST_TAKER_FEE_EXP)


def candidate_score(spread: float | None, depth: float, imbalance: float, in_band: bool, top_bid_usd: float, top_ask_usd: float) -> float:
    s = spread if (spread is not None and spread > 0) else 0.03
    score = (depth / max(s, 1e-6)) - (50.0 * abs(imbalance))
    if in_band:
        score += 500.0

    # Soft top-of-book bonus (preference only, not hard gate)
    weak_ok = (top_bid_usd >= MIN_TOP_BOOK_USD and top_ask_usd >= MIN_TOP_BOOK_USD)
    strong_ok = (top_bid_usd >= TOP_BOOK_STRONG_USD and top_ask_usd >= TOP_BOOK_STRONG_USD)
    if weak_ok:
        score += 250.0
    if strong_ok:
        score += 250.0
    return score


def find_open_group(slug: str, side: str):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    row = c.execute(
        """
        SELECT
            COALESCE(scale_group_id, CAST(MIN(id) AS TEXT)) AS scale_group_id,
            MIN(COALESCE(parent_trade_id, id)) AS parent_trade_id,
            SUM(COALESCE(remaining_size, size)) AS total_open_size,
            SUM(COALESCE(remaining_size, size) * entry) AS total_cost,
            CASE WHEN SUM(COALESCE(remaining_size, size)) > 0
                 THEN SUM(COALESCE(remaining_size, size) * entry) / SUM(COALESCE(remaining_size, size))
                 ELSE NULL END AS avg_entry_calc,
            MAX(COALESCE(scale_in_count, 0)) AS scale_in_count
        FROM trades
        WHERE slug = ? AND side = ? AND closed_ts IS NULL
        """,
        (slug, side),
    ).fetchone()
    conn.close()
    if not row or row[0] is None:
        return None
    return {
        "scale_group_id": str(row[0]),
        "parent_trade_id": int(row[1]) if row[1] is not None else None,
        "total_open_size": float(row[2] or 0.0),
        "avg_entry_calc": float(row[4]) if row[4] is not None else None,
        "scale_in_count": int(row[5] or 0),
    }


def recompute_group_avg_entry(slug: str, side: str):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        """
        UPDATE trades
        SET avg_entry = (
            SELECT CASE WHEN SUM(COALESCE(remaining_size, size)) > 0
                        THEN SUM(COALESCE(remaining_size, size) * entry) / SUM(COALESCE(remaining_size, size))
                        ELSE NULL END
            FROM trades t2
            WHERE t2.slug = trades.slug AND t2.side = trades.side AND t2.closed_ts IS NULL
        )
        WHERE slug = ? AND side = ? AND closed_ts IS NULL
        """,
        (slug, side),
    )
    conn.commit()
    conn.close()


def increment_group_scale_count(slug: str, side: str):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "UPDATE trades SET scale_in_count = COALESCE(scale_in_count, 0) + 1 WHERE slug = ? AND side = ? AND closed_ts IS NULL",
        (slug, side),
    )
    conn.commit()
    conn.close()


def can_add_same_side_entry(slug: str, side: str, candidate_entry: float) -> tuple[bool, str]:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    cols = [r[1] for r in c.execute("PRAGMA table_info(trades)").fetchall()]
    where_open = " AND closed_ts IS NULL" if "closed_ts" in cols else ""

    row = c.execute(
        f"""
        SELECT ts, entry
        FROM trades
        WHERE slug = ? AND side = ? {where_open}
        ORDER BY id DESC
        LIMIT 1
        """,
        (slug, side),
    ).fetchone()
    conn.close()

    if not row:
        return True, ""

    last_ts_raw, last_entry_raw = row
    last_entry = float(last_entry_raw)

    # Prevent rapid duplicate spam entries.
    try:
        last_ts = parse_ts(last_ts_raw)
        age = (datetime.now(UTC) - last_ts).total_seconds()
        if age < SAME_SIDE_ENTRY_COOLDOWN_SECONDS:
            return False, f"same-side cooldown {int(age)}s/{SAME_SIDE_ENTRY_COOLDOWN_SECONDS}s"
    except Exception:
        pass

    # Require better re-entry price by at least configured improvement.
    # Lower entry price is better for both YES and NO buys.
    if candidate_entry > (last_entry - MIN_REENTRY_PRICE_IMPROVEMENT):
        return False, f"reentry not improved (last={last_entry:.3f}, now={candidate_entry:.3f})"

    return True, ""


def maybe_auto_group_take_profit(slug: str, sell_yes_px: float | None, sell_no_px: float | None) -> int:
    if GROUP_TAKE_PROFIT_PCT <= 0:
        return 0

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    rows = c.execute(
        """
        SELECT id, side, entry, COALESCE(remaining_size, size) AS rem
        FROM trades
        WHERE slug = ? AND closed_ts IS NULL AND COALESCE(remaining_size, size) > 0
        ORDER BY id ASC
        """,
        (slug,),
    ).fetchall()

    by_side = {"BUY_YES": [], "BUY_NO": []}
    for tid, side, entry, rem in rows:
        if side in by_side:
            by_side[side].append((int(tid), float(entry), float(rem)))

    closed = 0
    now_iso = datetime.now(UTC).isoformat()

    for side, bucket in by_side.items():
        if len(bucket) < 2:  # only for grouped same-side stacks
            continue

        mark = sell_yes_px if side == "BUY_YES" else sell_no_px
        if mark is None:
            continue

        cost = sum(entry * rem for _, entry, rem in bucket)
        if cost <= 0:
            continue
        value = sum(float(mark) * rem for _, _, rem in bucket)
        pnl_pct = (value - cost) / cost

        if pnl_pct < GROUP_TAKE_PROFIT_PCT:
            continue

        for tid, entry, rem in bucket:
            pnl = (float(mark) - entry) * rem
            c.execute(
                "UPDATE trades SET closed_ts = ?, close_price = ?, close_note = ?, realized_pnl = COALESCE(realized_pnl, 0) + ?, remaining_size = 0 WHERE id = ?",
                (now_iso, float(mark), "group_take_profit", float(pnl), int(tid)),
            )
            closed += 1

        net = realized_net_pnl()
        print(
            f"ALERT GROUP_TAKE_PROFIT | slug={slug} side={side} legs={len(bucket)} pnl_pct={pnl_pct*100:.1f}% "
            f"mark={float(mark):.4f} net_realized={net:+.2f}"
        )

    conn.commit()
    conn.close()
    return closed


def _effective_stop_px(entry: float, ptd: int, peak_now: float | None = None) -> float:
    raw_floor = entry * (1.0 - AUTO_STOP_LOSS_PCT)
    cap_floor = entry * (1.0 - MAX_STOP_PCT)
    floor = max(raw_floor, cap_floor)
    if BREAKEVEN_AFTER_PARTIAL and int(ptd) == 1:
        floor = max(floor, entry * (1.0 + RUNNER_STOP_BUFFER_PCT))
        if TRAILING_STOP_AFTER_PARTIAL_PCT > 0 and peak_now is not None:
            floor = max(floor, float(peak_now) * (1.0 - TRAILING_STOP_AFTER_PARTIAL_PCT))
    return floor


def maybe_auto_stop_loss(slug: str, eta_seconds: int | None, sell_yes_px: float | None, sell_no_px: float | None, quote_ts: datetime | None = None) -> int:
    if AUTO_STOP_LOSS_PCT <= 0:
        return 0
    if is_stale_quote(quote_ts):
        print(f"STALE_QUOTE_SKIP | action=stop_loss | slug={slug}")
        return 0
    # Optional final-minute-only stop logic (legacy behavior).
    if STOP_LOSS_FINAL_MINUTE_ONLY and (eta_seconds is None or eta_seconds > 60):
        return 0

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    rows = c.execute(
        """
        SELECT id, ts, side, entry, COALESCE(remaining_size, size) AS size, COALESCE(partial_tp_done, 0) AS ptd, COALESCE(peak_price, entry) AS peak
        FROM trades
        WHERE slug = ? AND closed_ts IS NULL AND COALESCE(remaining_size, size) > 0
        ORDER BY id ASC
        """,
        (slug,),
    ).fetchall()

    # If any position on a side trips stop-loss, close ALL open positions on that side for this slug.
    stop_yes = False
    stop_no = False
    now_utc = datetime.now(UTC)
    for tid0, ts_raw, side, entry, size0, ptd, peak in rows:
        try:
            opened = parse_ts(ts_raw)
            if (now_utc - opened).total_seconds() < STOP_LOSS_ARMING_DELAY_SECONDS_SL:
                continue
        except Exception:
            continue

        entry = float(entry)
        mark = sell_yes_px if side == "BUY_YES" else sell_no_px
        if mark is None:
            continue

        # keep peak mark updated for trailing logic after partial TP
        peak_now = max(float(peak or entry), float(mark))
        c.execute("UPDATE trades SET peak_price=? WHERE id=?", (peak_now, int(tid0)))

        floor = _effective_stop_px(entry, int(ptd), peak_now)

        # time stop: after holding long enough, close if not making enough progress
        age_s = (now_utc - opened).total_seconds()
        pnl_pct = (float(mark) - entry) / max(entry, 1e-9)
        if TIME_STOP_SECONDS > 0 and age_s >= TIME_STOP_SECONDS and pnl_pct <= TIME_STOP_MAX_PNL_PCT:
            if side == "BUY_YES":
                stop_yes = True
            else:
                stop_no = True
            continue

        if side == "BUY_YES" and float(mark) <= floor:
            stop_yes = True
        elif side == "BUY_NO" and float(mark) <= floor:
            stop_no = True

    closed = 0
    now_iso = datetime.now(UTC).isoformat()
    for tid, ts_raw, side, entry, size, ptd, peak in rows:
        if side == "BUY_YES" and not stop_yes:
            continue
        if side == "BUY_NO" and not stop_no:
            continue

        entry = float(entry)
        size = float(size)
        close_price = sell_yes_px if side == "BUY_YES" else sell_no_px
        if close_price is None:
            continue

        trigger = float(close_price)
        effective_stop_px = _effective_stop_px(entry, int(ptd), float(peak or entry))
        effective_stop_pct = 1.0 - (effective_stop_px / max(entry, 1e-9))
        breach = max(0.0, effective_stop_px - trigger)
        breach_ticks = breach / 0.01
        late_exit = breach_ticks >= 2.0
        exit_limit = max(0.0, effective_stop_px - 0.01)
        if breach_ticks >= 2.0:
            # Emergency stop breach: use more marketable exit behavior (faster, fewer retries)
            delay_ms = random.randint(100, 350)
            retries = 0
            fill = max(0.0, trigger - 0.02)
            slip_ticks = (fill - trigger) / 0.01
        else:
            fill, delay_ms, retries, slip_ticks = simulate_exit_fill(trigger, spread=0.01, top_book_usd=30.0)
        pnl = (fill - entry) * size
        c.execute(
            "UPDATE trades SET closed_ts = ?, close_price = ?, close_note = ?, realized_pnl = COALESCE(realized_pnl, 0) + ?, remaining_size = 0, exit_trigger_price = ?, exit_fill_price = ?, slippage_ticks = ?, fill_delay_ms = ?, fill_retries = ? WHERE id = ?",
            (now_iso, float(fill), "auto_stop_loss", float(pnl), trigger, float(fill), float(slip_ticks), int(delay_ms), int(retries), int(tid)),
        )
        closed += 1
        side_txt = "UP" if side == "BUY_YES" else "DOWN"
        print(f"EXIT_TRIGGER | id={tid} token={side_txt} mark_at_trigger={trigger:.4f} stop_px={effective_stop_px:.4f} breach={breach:.4f} breach_ticks={breach_ticks:.1f} late_exit={str(late_exit).lower()} tp_hit=False sl_hit=True quote_age=0.0s")
        print(f"EXIT_ORDER | id={tid} type=SELL limit={exit_limit:.4f} attempt=1 pending_timeout={PENDING_ORDER_TIMEOUT_SEC}s")
        print(f"EXIT_FILLED | id={tid} fill={fill:.4f} slippage={slip_ticks:+.1f}t ttf={delay_ms}ms retries={retries}")
        realized_stop_pct = 1.0 - (float(fill) / max(entry, 1e-9))
        print(f"STOP_CLOSE | id={tid} entry={entry:.4f} mark_at_trigger={trigger:.4f} sell={fill:.4f} raw_sl={AUTO_STOP_LOSS_PCT:.2f} cap={MAX_STOP_PCT:.2f} effective={effective_stop_pct:.2f} realized_stop={realized_stop_pct:.2f} stop_px={effective_stop_px:.4f} breach_ticks={breach_ticks:.1f} late_exit={str(late_exit).lower()}")
        print(f"SELL SL | {side_txt} | id={tid} | pnl={pnl:+.2f}")

    conn.commit()
    conn.close()
    return closed


def maybe_auto_force_flatten_before_expiry(slug: str, eta_seconds: int | None, sell_yes_px: float | None, sell_no_px: float | None, quote_ts: datetime | None = None) -> int:
    if FORCE_FLAT_BEFORE_EXPIRY_SECONDS <= 0:
        return 0
    trigger_sec = max(1, min(FORCE_FLAT_BEFORE_EXPIRY_SECONDS, RUNNER_EXPIRY_CLOSE_SEC))
    if eta_seconds is None or eta_seconds > trigger_sec or eta_seconds <= 0:
        return 0
    if is_stale_quote(quote_ts):
        print(f"STALE_QUOTE_SKIP | action=pre_expiry_flatten | slug={slug}")
        return 0

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    rows = c.execute(
        """
        SELECT id, side, entry, COALESCE(remaining_size, size) AS size, COALESCE(partial_tp_done,0) AS ptd
        FROM trades
        WHERE slug = ? AND closed_ts IS NULL AND COALESCE(remaining_size, size) > 0
        ORDER BY id ASC
        """,
        (slug,),
    ).fetchall()

    closed = 0
    now_iso = datetime.now(UTC).isoformat()
    for tid, side, entry, size, ptd in rows:
        entry = float(entry)
        size = float(size)
        close_price = sell_yes_px if side == "BUY_YES" else sell_no_px
        if close_price is None:
            continue
        trigger = float(close_price)
        fill, delay_ms, retries, slip_ticks = simulate_exit_fill(trigger, spread=0.01, top_book_usd=40.0)
        pnl = (fill - entry) * size
        close_note = "runner_expiry_close" if int(ptd) == 1 else "pre_expiry_auto_close"
        c.execute(
            "UPDATE trades SET closed_ts = ?, close_price = ?, close_note = ?, realized_pnl = COALESCE(realized_pnl, 0) + ?, remaining_size = 0, exit_trigger_price = ?, exit_fill_price = ?, slippage_ticks = ?, fill_delay_ms = ?, fill_retries = ? WHERE id = ?",
            (now_iso, float(fill), close_note, float(pnl), trigger, float(fill), float(slip_ticks), int(delay_ms), int(retries), int(tid)),
        )
        closed += 1
        side_txt = "UP" if side == "BUY_YES" else "DOWN"
        if int(ptd) == 1:
            print(f"RUNNER_CLOSE | id={tid} token={side_txt} reason=expiry eta={eta_seconds}s pnl={pnl:+.2f}")
        else:
            print(f"SELL PRE_EXPIRY | {side_txt} | id={tid} | eta={eta_seconds}s | pnl={pnl:+.2f}")

    conn.commit()
    conn.close()
    return closed


def maybe_auto_close_expired_round(slug: str, eta_seconds: int | None, sell_yes_px: float | None, sell_no_px: float | None, quote_ts: datetime | None = None) -> int:
    if eta_seconds is None or eta_seconds > 0:
        return 0
    if is_stale_quote(quote_ts):
        print(f"STALE_QUOTE_SKIP | action=round_expired_close | slug={slug}")
        return 0

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    rows = c.execute(
        """
        SELECT id, side, entry, COALESCE(remaining_size, size) AS size, COALESCE(partial_tp_done,0) AS ptd
        FROM trades
        WHERE slug = ? AND closed_ts IS NULL AND COALESCE(remaining_size, size) > 0
        ORDER BY id ASC
        """,
        (slug,),
    ).fetchall()

    closed = 0
    now_iso = datetime.now(UTC).isoformat()
    for tid, side, entry, size, ptd in rows:
        entry = float(entry)
        size = float(size)
        close_price = sell_yes_px if side == "BUY_YES" else sell_no_px
        if close_price is None:
            continue
        trigger = float(close_price)
        fill, delay_ms, retries, slip_ticks = simulate_exit_fill(trigger, spread=0.01, top_book_usd=40.0)
        pnl = (fill - entry) * size
        c.execute(
            "UPDATE trades SET closed_ts = ?, close_price = ?, close_note = ?, realized_pnl = COALESCE(realized_pnl, 0) + ?, remaining_size = 0, exit_trigger_price = ?, exit_fill_price = ?, slippage_ticks = ?, fill_delay_ms = ?, fill_retries = ? WHERE id = ?",
            (now_iso, float(fill), "round_expired_auto_close", float(pnl), trigger, float(fill), float(slip_ticks), int(delay_ms), int(retries), int(tid)),
        )
        closed += 1
        side_txt = "UP" if side == "BUY_YES" else "DOWN"
        print(f"EXIT_TRIGGER | id={tid} token={side_txt} mark_bid={trigger:.4f} tp_hit=False sl_hit=False quote_age=0.0s")
        print(f"EXIT_ORDER | id={tid} type=SELL limit={max(0.0, trigger-0.01):.4f} attempt=1")
        print(f"EXIT_FILLED | id={tid} fill={fill:.4f} slippage={slip_ticks:+.1f}t ttf={delay_ms}ms retries={retries}")
        print(f"SELL EXPIRY | {side_txt} | id={tid} | pnl={pnl:+.2f}")

    conn.commit()
    conn.close()
    return closed


def maybe_close_any_expired_open_positions() -> int:
    """Safety sweep: close any leftover open trades from expired rounds, even if slug changed."""
    now_ts = int(datetime.now(UTC).timestamp())
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    rows = c.execute(
        """
        SELECT id, slug, side, entry, COALESCE(remaining_size, size) AS size
        FROM trades
        WHERE closed_ts IS NULL AND COALESCE(remaining_size, size) > 0
        ORDER BY id ASC
        """
    ).fetchall()

    closed = 0
    for tid, slug, side, entry, size in rows:
        try:
            sfx = int(str(slug).rsplit("-", 1)[-1])
        except Exception:
            continue
        if now_ts <= (sfx + ROUND_MINUTES * 60):
            continue

        # expired: best-effort mark from Gamma at close time
        market, _ = discover(SERIES_PREFIX, ROUND_MINUTES, force_slug=slug)
        yes_px = market.yes_price if market is not None else None
        if yes_px is None:
            continue

        close_price = yes_px if side == "BUY_YES" else (1.0 - yes_px)
        trigger = float(close_price)
        fill, delay_ms, retries, slip_ticks = simulate_exit_fill(trigger, spread=0.01, top_book_usd=25.0)
        pnl = (fill - float(entry)) * float(size)
        c.execute(
            "UPDATE trades SET closed_ts = ?, close_price = ?, close_note = ?, realized_pnl = COALESCE(realized_pnl, 0) + ?, remaining_size = 0, exit_trigger_price = ?, exit_fill_price = ?, slippage_ticks = ?, fill_delay_ms = ?, fill_retries = ? WHERE id = ?",
            (datetime.now(UTC).isoformat(), float(fill), "expired_sweep_auto_close", float(pnl), trigger, float(fill), float(slip_ticks), int(delay_ms), int(retries), int(tid)),
        )
        closed += 1
        print(f"EXIT_TRIGGER | id={tid} token={side} mark_bid={trigger:.4f} tp_hit=False sl_hit=False quote_age=0.0s")
        print(f"EXIT_ORDER | id={tid} type=SELL limit={max(0.0, trigger-0.01):.4f} attempt=1")
        print(f"EXIT_FILLED | id={tid} fill={fill:.4f} slippage={slip_ticks:+.1f}t ttf={delay_ms}ms retries={retries}")

    conn.commit()
    conn.close()
    return closed


def _series_prefix_from_slug(slug: str) -> str:
    try:
        i = str(slug).rfind("-5m-")
        if i > 0:
            return str(slug)[:i]
    except Exception:
        pass
    return SERIES_PREFIX


def maybe_manage_all_open_slug_exits(ob: OBReader) -> int:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    slugs = [r[0] for r in c.execute("SELECT DISTINCT slug FROM trades WHERE closed_ts IS NULL AND COALESCE(remaining_size,size)>0").fetchall()]
    conn.close()

    total_closed = 0
    for slug in slugs:
        pref = _series_prefix_from_slug(slug)
        market, derr = discover(pref, ROUND_MINUTES, force_slug=slug)
        if derr or market is None:
            continue

        yes_book, yerr = ob.read(market.yes_token_id) if market.yes_token_id else (None, "missing_yes_token")
        no_book, nerr = ob.read(market.no_token_id) if market.no_token_id else (None, "missing_no_token")
        yes_best_bid = yes_book.best_bid if (yerr is None and yes_book is not None) else market.best_bid
        yes_best_ask = yes_book.best_ask if (yerr is None and yes_book is not None) else market.best_ask
        no_best_bid = no_book.best_bid if (nerr is None and no_book is not None) else None

        sell_yes_px = yes_best_bid if yes_best_bid is not None else market.yes_price
        sell_no_px = no_best_bid if no_best_bid is not None else ((1.0 - yes_best_ask) if yes_best_ask is not None else market.no_price)
        quote_ts = datetime.now(UTC)
        eta_now = seconds_to_next(market.slug, market.end_ts)

        total_closed += maybe_auto_force_flatten_before_expiry(market.slug, eta_now, sell_yes_px, sell_no_px, quote_ts)
        total_closed += maybe_auto_close_expired_round(market.slug, eta_now, sell_yes_px, sell_no_px, quote_ts)
        total_closed += maybe_auto_group_take_profit(market.slug, sell_yes_px, sell_no_px)
        total_closed += maybe_auto_take_profit(market.slug, sell_yes_px, sell_no_px, quote_ts)
        total_closed += maybe_auto_stop_loss(market.slug, eta_now, sell_yes_px, sell_no_px, quote_ts)

    return total_closed


def maybe_auto_close_stale_positions() -> int:
    if MAX_HOLD_SECONDS <= 0:
        return 0

    now = datetime.now(UTC)
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    rows = c.execute(
        """
        SELECT id, ts, slug, side, entry, COALESCE(remaining_size, size) AS size
        FROM trades
        WHERE closed_ts IS NULL AND COALESCE(remaining_size, size) > 0
        ORDER BY id ASC
        """
    ).fetchall()

    closed = 0
    for tid, ts, slug, side, entry, size in rows:
        try:
            opened = parse_ts(ts)
        except Exception:
            continue

        age = (now - opened).total_seconds()
        if age < MAX_HOLD_SECONDS:
            continue

        market, _ = discover(SERIES_PREFIX, ROUND_MINUTES, force_slug=slug)
        yes_px = market.yes_price if market is not None else None
        if yes_px is None:
            continue

        close_price = yes_px if side == "BUY_YES" else (1.0 - yes_px)
        trigger = float(close_price)
        fill, delay_ms, retries, slip_ticks = simulate_exit_fill(trigger, spread=0.01, top_book_usd=25.0)
        pnl = (fill - float(entry)) * float(size)
        c.execute(
            "UPDATE trades SET closed_ts = ?, close_price = ?, close_note = ?, realized_pnl = COALESCE(realized_pnl, 0) + ?, remaining_size = 0, exit_trigger_price = ?, exit_fill_price = ?, slippage_ticks = ?, fill_delay_ms = ?, fill_retries = ? WHERE id = ?",
            (now.isoformat(), float(fill), "max_hold_auto_close", float(pnl), trigger, float(fill), float(slip_ticks), int(delay_ms), int(retries), int(tid)),
        )
        closed += 1
        print(f"EXIT_TRIGGER | id={tid} token={side} mark_bid={trigger:.4f} tp_hit=False sl_hit=False quote_age=0.0s")
        print(f"EXIT_ORDER | id={tid} type=SELL limit={max(0.0, trigger-0.01):.4f} attempt=1")
        print(f"EXIT_FILLED | id={tid} fill={fill:.4f} slippage={slip_ticks:+.1f}t ttf={delay_ms}ms retries={retries}")

    conn.commit()
    conn.close()
    return closed


def main():
    if ROUND_MINUTES <= 0:
        die(E_CONFIG, "ROUND_MINUTES must be > 0")

    init_db()
    ob = OBReader()
    bankroll = STARTING_BANKROLL

    print("=" * 72)
    print(f"POLYMARKET BOT V5 | {BUILD_TAG}")
    print("=" * 72)
    print(f"BOOT | engine={ENGINE_TAG} | build={BUILD_TAG} | file={os.path.abspath(__file__)}")
    print(
        f"CONFIG | edge={MIN_EDGE:.3f} prob_delta={MIN_PROB_DISTANCE:.3f} side_adv={MIN_SIDE_ADVANTAGE:.3f} "
        f"sl={AUTO_STOP_LOSS_PCT:.2f} max_sl={MAX_STOP_PCT:.2f} tp={AUTO_TAKE_PROFIT_PCT:.2f} runner={TP_PRINCIPAL_TRIGGER_PCT:.2f}/{TP_PRINCIPAL_SELL_FRAC:.2f} be_buf={RUNNER_STOP_BUFFER_PCT:.2f} trail={TRAILING_STOP_AFTER_PARTIAL_PCT:.2f} tstop={TIME_STOP_SECONDS}s/{TIME_STOP_MAX_PNL_PCT:.2f} "
        f"entries_round={MAX_ENTRIES_PER_ROUND} same_side_open_cap={MAX_SAME_SIDE_OPEN_PER_ROUND} prefixes={','.join(SERIES_PREFIXES)} max_conc={MAX_CONCURRENT_TRADES} "
        f"window={ENTRY_WINDOW_START_SECONDS}-{ENTRY_WINDOW_END_SECONDS}s loop={LOOP_SECONDS}s stop_cooldown={STOPLOSS_REENTRY_COOLDOWN_SECONDS}s sl_arm={STOP_LOSS_ARMING_DELAY_SECONDS_SL}s"
    )

    current_force_slug = FORCE_SLUG
    last_logged_slug = None

    while True:
        try:
            write_state("loop", ob=ob)
            cleanup_expired_intents()
            maybe_close_any_expired_open_positions()
            maybe_auto_close_stale_positions()
            maybe_manage_all_open_slug_exits(ob)

            day_count = trades_today()
            if MAX_TRADES_PER_DAY > 0 and day_count >= MAX_TRADES_PER_DAY:
                vprint(f"No trade | daily cap {day_count}/{MAX_TRADES_PER_DAY}")
                time.sleep(LOOP_SECONDS)
                continue

            # Multi-market candidate discovery (CLOB-first quality checks).
            candidates = []
            prefixes = [SERIES_PREFIX] if current_force_slug else SERIES_PREFIXES
            for pref in prefixes:
                market, derr = discover(pref, ROUND_MINUTES, force_slug=current_force_slug or None)
                if derr or market is None:
                    if derr:
                        vprint(f"CANDIDATE_FAIL | prefix={pref} | {derr}")
                    continue

                # Token/outcome sanity
                if not market.yes_token_id or not market.no_token_id:
                    vprint(f"CANDIDATE_FAIL | prefix={pref} | slug={market.slug} | reason=missing_token_ids")
                    continue

                yes_book, yerr = ob.read(market.yes_token_id)
                no_book, nerr = ob.read(market.no_token_id)
                if yerr or nerr or yes_book is None or no_book is None:
                    vprint(f"CANDIDATE_FAIL | prefix={pref} | slug={market.slug} | reason=clob_quote_fail")
                    continue

                spread = yes_book.spread
                depth = yes_book.depth_top5
                depth_usd = yes_book.depth_top5_usd
                yes_bid = yes_book.best_bid
                yes_ask = yes_book.best_ask
                top_bid_usd = yes_book.top_bid_usd
                top_ask_usd = yes_book.top_ask_usd

                # Volume gate is optional; when disabled (<=0) rely on execution quality gates.
                if MIN_VOLUME24H <= 0:
                    vol_ok = True
                else:
                    vol_ok = (market.volume24h is None) or (market.volume24h >= MIN_VOLUME24H)

                gate_ok = (
                    (spread is not None and spread <= MAX_SPREAD)
                    and depth >= MIN_DEPTH_TOP5
                    and depth_usd >= MIN_DEPTH_TOP5_USD
                    and vol_ok
                )
                fail_reason = ""
                if not gate_ok:
                    if spread is None or spread > MAX_SPREAD:
                        fail_reason = "spread"
                    elif depth < MIN_DEPTH_TOP5:
                        fail_reason = "depth"
                    elif depth_usd < MIN_DEPTH_TOP5_USD:
                        fail_reason = "depth_usd"
                    elif not vol_ok:
                        fail_reason = "volume24h"

                weak_top = (top_bid_usd >= MIN_TOP_BOOK_USD and top_ask_usd >= MIN_TOP_BOOK_USD)
                strong_top = (top_bid_usd >= TOP_BOOK_STRONG_USD and top_ask_usd >= TOP_BOOK_STRONG_USD)
                vprint(
                    f"CANDIDATE | engine={ENGINE_TAG} build={BUILD_TAG} | prefix={pref} slug={market.slug} suffix={market.suffix} market_id={market.market_id} "
                    f"bid={yes_bid} ask={yes_ask} spread={spread} depth={depth:.1f} depth_usd={depth_usd:.1f} top_bid_usd={top_bid_usd:.1f} top_ask_usd={top_ask_usd:.1f} "
                    f"top_bonus={'strong' if strong_top else ('weak' if weak_top else 'none')} vol24h={market.volume24h} gate={gate_ok} reason={fail_reason or 'ok'}"
                )

                if gate_ok:
                    in_band = (BUY_YES_MIN_ENTRY <= (yes_ask or market.yes_price) < BUY_YES_MAX_ENTRY) or (
                        BUY_NO_MIN_ENTRY <= (no_book.best_ask or market.no_price) < BUY_NO_MAX_ENTRY
                    )
                    score = candidate_score(spread, depth, yes_book.imbalance, in_band, top_bid_usd, top_ask_usd)
                    candidates.append((score, pref, market, yes_book, no_book))

            if not candidates:
                time.sleep(LOOP_SECONDS)
                continue

            candidates.sort(key=lambda x: x[0], reverse=True)
            pending_n = pending_intents_total()
            available_slots = max(0, MAX_CONCURRENT_TRADES - open_positions_total() - pending_n)
            if available_slots <= 0:
                vprint(f"SELECTED | n=0 reason=no_available_slots max_concurrent={MAX_CONCURRENT_TRADES} pending={pending_n}")
                time.sleep(LOOP_SECONDS)
                continue

            selected = []
            used_keys = set()
            for score, pref, mkt, bok_yes, bok_no in candidates:
                key = (pref, mkt.suffix)
                if key in used_keys:
                    continue
                if trades_taken_on_slug(mkt.slug) >= MAX_TRADES_PER_SLUG:
                    continue
                selected.append((score, pref, mkt, bok_yes, bok_no))
                used_keys.add(key)
                if len(selected) >= available_slots:
                    break

            if not selected:
                vprint("SELECTED | n=0 reason=all_candidates_blocked_by_slug_cap_or_keys")
                time.sleep(LOOP_SECONDS)
                continue

            picked_txt = ", ".join([f"{x[1]}:{x[2].slug}:{x[0]:.1f}" for x in selected])
            vprint(f"SELECTED | n={len(selected)} -> {picked_txt}")

            # Current execution path processes one candidate per loop (highest-ranked selected).
            _, chosen_prefix, market, book, no_book = selected[0]

            if market.slug != last_logged_slug:
                print(
                    f"Market selected | prefix={chosen_prefix} | slug={market.slug} | suffix={market.suffix} | market_id={market.market_id} "
                    f"| yes_token_id={market.yes_token_id} | no_token_id={market.no_token_id}"
                )
                last_logged_slug = market.slug

            slug_l = str(market.slug).lower()
            if slug_l.startswith("sol-"):
                asset = "SOL"
            elif slug_l.startswith("eth-"):
                asset = "ETH"
            elif slug_l.startswith("xrp-"):
                asset = "XRP"
            else:
                asset = "BTC"
            prob, stext, serr = signal_up_prob(asset=asset)
            if serr:
                print(serr)
                time.sleep(LOOP_SECONDS)
                continue

            # book already fetched during candidate ranking
            berr = None
            spread = book.spread
            depth = book.depth_top5
            imbalance = book.imbalance

            yes_best_bid = book.best_bid if (berr is None and book is not None) else market.best_bid
            yes_best_ask = book.best_ask if (berr is None and book is not None) else market.best_ask

            no_best_bid = no_book.best_bid if no_book is not None else None
            no_best_ask = no_book.best_ask if no_book is not None else None

            buy_yes_px = yes_best_ask if yes_best_ask is not None else market.yes_price
            buy_no_px = no_best_ask if no_best_ask is not None else ((1.0 - yes_best_bid) if yes_best_bid is not None else market.no_price)
            sell_yes_px = yes_best_bid if yes_best_bid is not None else market.yes_price
            sell_no_px = no_best_bid if no_best_bid is not None else ((1.0 - yes_best_ask) if yes_best_ask is not None else market.no_price)
            quote_ts = datetime.now(UTC)

            if no_best_bid is None or no_best_ask is None:
                vprint(f"MARK_FALLBACK | reason=no_quote_for_NO | slug={market.slug}")

            # Use realtime book as primary anchor (Gamma can lag on 5m rounds).
            realtime_yes = None
            if yes_best_bid is not None and yes_best_ask is not None:
                realtime_yes = (yes_best_bid + yes_best_ask) / 2.0
            elif book is not None and book.midpoint is not None:
                realtime_yes = book.midpoint
            elif yes_best_ask is not None:
                realtime_yes = yes_best_ask
            elif yes_best_bid is not None:
                realtime_yes = yes_best_bid

            # Only guard if we have a realtime anchor; compare buy_yes vs realtime, not stale gamma.
            if realtime_yes is not None:
                mismatch = abs(buy_yes_px - realtime_yes)
                if mismatch > MAX_QUOTE_MISMATCH:
                    print(
                        f"SKIP_BAD_QUOTE_MISMATCH | slug={market.slug} | realtime_yes={realtime_yes:.3f} "
                        f"| buy_yes={buy_yes_px:.3f} | diff={mismatch:.3f}"
                    )
                    time.sleep(LOOP_SECONDS)
                    continue

            eta_now = seconds_to_next(market.slug, market.end_ts)

            # Round timeline window guard
            now_ts = int(datetime.now(UTC).timestamp())
            try:
                round_start_ts = int(str(market.slug).rsplit("-", 1)[-1])
            except Exception:
                round_start_ts = None
            elapsed = (now_ts - round_start_ts) if round_start_ts is not None else None

            vprint(
                f"Round: {market.slug} | yes={market.yes_price:.3f} | buy_yes={buy_yes_px:.3f} | buy_no={buy_no_px:.3f} | elapsed={elapsed}s | left={eta_now}s | {stext} | spread={spread} | depth={depth:.1f} | imbalance={imbalance:.2f}"
            )

            if eta_now is not None and eta_now < MIN_SECONDS_TO_EXPIRY:
                vprint(f"No trade | too close to expiry ({eta_now}s < {MIN_SECONDS_TO_EXPIRY}s)")
                time.sleep(LOOP_SECONDS)
                continue
            if elapsed is not None and (elapsed < ENTRY_WINDOW_START_SECONDS or elapsed > ENTRY_WINDOW_END_SECONDS):
                vprint(f"No trade | outside entry window ({elapsed}s, allowed {ENTRY_WINDOW_START_SECONDS}-{ENTRY_WINDOW_END_SECONDS}s)")
                time.sleep(LOOP_SECONDS)
                continue

            if trades_taken_on_slug(market.slug) >= MAX_TRADES_PER_SLUG:
                eta = eta_now
                eta_safe = max(0, eta) if eta is not None else None
                eta_txt = f" | next in {eta_safe}s" if eta_safe is not None else ""
                vprint(f"Round: {market.slug} | No trade | slug cap {MAX_TRADES_PER_SLUG}{eta_txt}")
                time.sleep(LOOP_SECONDS)
                continue

            round_count = open_positions_this_round(market.slug)
            if round_count >= MAX_ENTRIES_PER_ROUND:
                eta = eta_now
                eta_safe = max(0, eta) if eta is not None else None
                eta_txt = f" | next in {eta_safe}s" if eta_safe is not None else ""
                vprint(f"Round: {market.slug} | No trade | open cap {round_count}/{MAX_ENTRIES_PER_ROUND}{eta_txt}")

                # If pinned slug is already expired, roll to next round automatically.
                if current_force_slug and AUTO_ROLL_FORCE_SLUG and eta is not None and eta < 0:
                    nxt = _advance_slug_once(current_force_slug)
                    if nxt != current_force_slug:
                        current_force_slug = nxt
                        print(f"Auto-rolled forced slug -> {current_force_slug}")

                time.sleep(LOOP_SECONDS)
                continue

            if spread is not None and spread > MAX_SPREAD:
                vprint("No trade | spread too wide")
                time.sleep(LOOP_SECONDS)
                continue
            if depth < MIN_DEPTH_TOP5:
                vprint("No trade | depth too thin")
                time.sleep(LOOP_SECONDS)
                continue
            if has_recent_stoploss(market.slug):
                vprint(f"No trade | stop-loss cooldown active ({STOPLOSS_REENTRY_COOLDOWN_SECONDS}s)")
                time.sleep(LOOP_SECONDS)
                continue
            if not (ENTRY_PRICE_FLOOR <= buy_yes_px <= ENTRY_PRICE_CEIL):
                vprint(f"No trade | buy_yes out of range ({buy_yes_px:.3f})")
                time.sleep(LOOP_SECONDS)
                continue
            if not (ENTRY_PRICE_FLOOR <= buy_no_px <= ENTRY_PRICE_CEIL):
                vprint(f"No trade | buy_no out of range ({buy_no_px:.3f})")
                time.sleep(LOOP_SECONDS)
                continue

            regime, votes = parse_regime_votes(stext or "")
            rsi14 = None
            try:
                m_rsi = re.search(r"rsi14\s*=\s*([0-9]+(?:\.[0-9]+)?)", str(stext or ""), flags=re.IGNORECASE)
                if m_rsi:
                    rsi14 = float(m_rsi.group(1))
            except Exception:
                rsi14 = None
            edge_yes = prob - buy_yes_px
            edge_no = (1.0 - prob) - buy_no_px
            fee_yes = estimated_taker_fee_per_share(buy_yes_px) * 2.0
            fee_no = estimated_taker_fee_per_share(buy_no_px) * 2.0
            edge_yes_net = edge_yes - fee_yes - NET_EDGE_BUFFER
            edge_no_net = edge_no - fee_no - NET_EDGE_BUFFER

            # Directional guard: only take side aligned with forecast, and skip weak 50/50 forecasts.
            prob_delta = abs(prob - 0.5)
            if prob_delta < MIN_PROB_DISTANCE:
                vprint(f"No trade | forecast too close to 50/50 (prob={prob:.3f}, min_delta={MIN_PROB_DISTANCE:.3f})")
                time.sleep(LOOP_SECONDS)
                continue

            side = None
            entry = None
            edge = 0.0
            trade_token_id = None
            entry_source = "gamma"
            long_allowed = True
            short_allowed = True
            mixed_probe = False
            if STRONG_REGIME_ONLY and regime is not None and votes is not None:
                if regime == "BULL":
                    long_allowed = (votes >= BULL_MIN_VOTES)
                    short_allowed = False
                elif regime == "BEAR":
                    long_allowed = False
                    short_allowed = (votes <= BEAR_MAX_VOTES)
                elif regime == "MIXED":
                    if MIXED_PROBE_ENABLED:
                        long_allowed = True
                        short_allowed = True
                        mixed_probe = True
                    else:
                        long_allowed = False
                        short_allowed = False

            side_yes_min_edge = MIN_EDGE
            side_no_min_edge = MIN_EDGE
            yes_recent = recent_side_realized_pnl("BUY_YES", SIDE_PERF_LOOKBACK)
            no_recent = recent_side_realized_pnl("BUY_NO", SIDE_PERF_LOOKBACK)
            if yes_recent < 0:
                side_yes_min_edge += LOSING_SIDE_EDGE_PENALTY
            if no_recent < 0:
                side_no_min_edge += LOSING_SIDE_EDGE_PENALTY

            yes_ok = edge_yes_net >= side_yes_min_edge and long_allowed
            no_ok = edge_no_net >= side_no_min_edge and short_allowed

            # Fair-value discount guard: only buy when market is below modeled fair value by a margin.
            yes_fair_limit = prob * (1.0 - FAIR_VALUE_DISCOUNT_PCT)
            no_fair = (1.0 - prob)
            no_fair_limit = no_fair * (1.0 - FAIR_VALUE_DISCOUNT_PCT)
            yes_ok = yes_ok and (buy_yes_px <= yes_fair_limit)
            no_ok = no_ok and (buy_no_px <= no_fair_limit)

            # Side-specific profitable entry zones from empirical stats.
            yes_ok = yes_ok and (BUY_YES_MIN_ENTRY <= buy_yes_px < BUY_YES_MAX_ENTRY)
            no_ok = no_ok and (BUY_NO_MIN_ENTRY <= buy_no_px < BUY_NO_MAX_ENTRY)

            # Avoid coin-flip entries: require one side to clearly dominate.
            if yes_ok and no_ok and abs(edge_yes_net - edge_no_net) < MIN_SIDE_ADVANTAGE:
                print(
                    f"No trade | side advantage too small (edge_yes={edge_yes_net:.4f}, edge_no={edge_no_net:.4f}, min={MIN_SIDE_ADVANTAGE:.4f})"
                )
                time.sleep(LOOP_SECONDS)
                continue

            prefer_yes = prob > 0.5
            prefer_no = prob < 0.5

            if prefer_yes and yes_ok and (not no_ok or edge_yes_net >= edge_no_net):
                side = "BUY_YES"
                entry = buy_yes_px
                edge = edge_yes_net
                trade_token_id = market.yes_token_id
                entry_source = "clob" if yes_best_ask is not None else "gamma"
            elif prefer_no and no_ok and (not yes_ok or edge_no_net >= edge_yes_net):
                side = "BUY_NO"
                entry = buy_no_px
                edge = edge_no_net
                trade_token_id = market.no_token_id
                entry_source = "clob" if no_best_ask is not None else "gamma"

            if side == "BUY_YES" and rsi14 is not None and rsi14 > MAX_RSI_FOR_LONG:
                vprint(f"No trade | long blocked by RSI ({rsi14:.1f} > {MAX_RSI_FOR_LONG:.1f})")
                time.sleep(LOOP_SECONDS)
                continue

            if not side:
                regime_txt = f"regime={regime} votes={votes}" if regime is not None else "regime=n/a"
                print(
                    f"No trade | edge_yes={edge_yes_net:.4f} edge_no={edge_no_net:.4f} "
                    f"| fair_yes<= {yes_fair_limit:.3f} fair_no<= {no_fair_limit:.3f} "
                    f"| {regime_txt}"
                )
                time.sleep(LOOP_SECONDS)
                continue

            if has_pending_intent(market.slug, side):
                vprint("No trade | pending intent exists for slug/side")
                time.sleep(LOOP_SECONDS)
                continue

            if has_open_opposite_side(market.slug, side):
                vprint("No trade | opposite side already open this round")
                time.sleep(LOOP_SECONDS)
                continue

            if open_same_side_count(market.slug, side) >= MAX_SAME_SIDE_OPEN_PER_ROUND:
                vprint(f"No trade | same-side open cap {MAX_SAME_SIDE_OPEN_PER_ROUND}")
                time.sleep(LOOP_SECONDS)
                continue

            group = find_open_group(market.slug, side)
            is_scale_in = 0
            parent_trade_id = None
            entry_tier = 1
            scale_group_id = None
            scale_trigger_note = None
            scale_in_count_for_insert = 0

            if group and SCALE_IN_ENABLED:
                avg_entry_grp = float(group.get("avg_entry_calc") or entry)
                grp_count = int(group.get("scale_in_count") or 0)
                if grp_count >= MAX_SCALE_INS_PER_GROUP:
                    vprint(f"No trade | scale-in cap reached {grp_count}/{MAX_SCALE_INS_PER_GROUP}")
                    time.sleep(LOOP_SECONDS)
                    continue
                if float(entry) > (avg_entry_grp - SCALE_IN_MIN_IMPROVEMENT):
                    vprint(f"No trade | scale-in not improved (avg={avg_entry_grp:.3f}, now={float(entry):.3f})")
                    time.sleep(LOOP_SECONDS)
                    continue
                is_scale_in = 1
                parent_trade_id = int(group.get("parent_trade_id") or 0) or None
                entry_tier = grp_count + 2
                scale_group_id = str(group.get("scale_group_id") or "")
                scale_trigger_note = f"improved_entry>={SCALE_IN_MIN_IMPROVEMENT:.3f}"
                scale_in_count_for_insert = grp_count
            else:
                allow_entry, block_reason = can_add_same_side_entry(market.slug, side, float(entry))
                if not allow_entry:
                    vprint(f"No trade | {block_reason}")
                    time.sleep(LOOP_SECONDS)
                    continue

            balance_now = current_balance_realized_only()
            risk_mult = 1.0
            # High-conviction sizing only for strong YES setups (never guaranteed, still risk-managed).
            if (
                side == "BUY_YES"
                and regime == "BULL"
                and (votes is not None and votes >= HIGH_CONV_MIN_VOTES)
                and prob >= HIGH_CONV_MIN_PROB
                and edge >= HIGH_CONV_MIN_EDGE
            ):
                risk_mult = max(1.0, HIGH_CONVICTION_MULTIPLIER)

            risk = balance_now * RISK_PCT * risk_mult
            if mixed_probe:
                risk *= max(0.05, min(1.0, MIXED_RISK_MULT))
            if elapsed is not None and elapsed >= LATE_WINDOW_START_SECONDS:
                risk *= max(0.10, min(1.0, LATE_WINDOW_RISK_MULT))
            size = risk / max(entry, 1e-6)
            note = (
                f"edge={edge:.4f} spread={spread} depth={depth:.1f} imbalance={imbalance:.2f} "
                f"source={entry_source} bal={balance_now:.2f} risk={risk:.2f} mult={risk_mult:.2f}"
            )
            intent_id = reserve_intent(market.slug, side)
            if intent_id <= 0:
                vprint("No trade | failed to reserve pending intent")
                time.sleep(LOOP_SECONDS)
                continue
            try:
                log_trade(
                    market.slug, market.market_id, side, entry, size, edge, note, trade_token_id, entry_source,
                    parent_trade_id=parent_trade_id, entry_tier=entry_tier, is_scale_in=is_scale_in,
                    scale_group_id=scale_group_id, scale_trigger_note=scale_trigger_note, scale_in_count=scale_in_count_for_insert,
                )
                resolve_intent(intent_id, "DONE")
            except Exception:
                resolve_intent(intent_id, "FAILED")
                raise
            if is_scale_in:
                recompute_group_avg_entry(market.slug, side)
                increment_group_scale_count(market.slug, side)
            side_txt = "UP" if side == "BUY_YES" else "DOWN"
            print(f"BUY {side_txt} | entry={entry:.4f} | size={size:.2f}")
            write_state(f"BUY {side_txt} entry={entry:.4f}", ob=ob)

            time.sleep(LOOP_SECONDS)
        except KeyboardInterrupt:
            print("Stopping V4.")
            break
        except Exception as e:
            print(f"[ERR 1999] loop_error: {e}")
            write_state(f"loop_error: {e}")
            time.sleep(LOOP_SECONDS)


if __name__ == "__main__":
    main()



