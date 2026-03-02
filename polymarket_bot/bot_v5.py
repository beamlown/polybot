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
GROUP_TAKE_PROFIT_PCT = float(os.getenv("GROUP_TAKE_PROFIT_PCT", "0.30"))
BREAKEVEN_AFTER_PARTIAL = os.getenv("BREAKEVEN_AFTER_PARTIAL", "true").strip().lower() in ("1", "true", "yes", "on")
BREAKEVEN_BUFFER_PCT = float(os.getenv("BREAKEVEN_BUFFER_PCT", "0.01"))
AUTO_STOP_LOSS_PCT = float(os.getenv("AUTO_STOP_LOSS_PCT", "0"))
MAX_QUOTE_MISMATCH = float(os.getenv("MAX_QUOTE_MISMATCH", "0.12"))
STOPLOSS_REENTRY_COOLDOWN_SECONDS = int(os.getenv("STOPLOSS_REENTRY_COOLDOWN_SECONDS", "45"))
STOP_LOSS_ARMING_DELAY_SECONDS = int(os.getenv("STOP_LOSS_ARMING_DELAY_SECONDS", "15"))
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
MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", "5"))
MAX_ENTRIES_PER_ROUND = int(os.getenv("MAX_ENTRIES_PER_ROUND", "1"))
MAX_TRADES_PER_SLUG = int(os.getenv("MAX_TRADES_PER_SLUG", "1"))
RISK_PCT = float(os.getenv("MAX_RISK_PER_TRADE_PCT", "0.005"))
MAX_SPREAD = float(os.getenv("MAX_SPREAD", "0.03"))
MIN_DEPTH_TOP5 = float(os.getenv("MIN_DEPTH_TOP5", "50"))
LOOP_SECONDS = int(os.getenv("LOOP_SECONDS", "5"))
QUIET_LOGGING = os.getenv("QUIET_LOGGING", "true").strip().lower() in ("1", "true", "yes", "on")
MIN_SECONDS_TO_EXPIRY = int(os.getenv("MIN_SECONDS_TO_EXPIRY", "0"))
ENTRY_WINDOW_START_SECONDS = int(os.getenv("ENTRY_WINDOW_START_SECONDS", "0"))
ENTRY_WINDOW_END_SECONDS = int(os.getenv("ENTRY_WINDOW_END_SECONDS", "999999"))
DB = "trades_v4.db"
BUILD_TAG = "v5.2026-03-01.001"
ENGINE_TAG = "v5_liquidity_softbook"


def die(code: int, msg: str):
    print(fmt(code, msg))
    sys.exit(code)


def vprint(msg: str):
    if not QUIET_LOGGING:
        print(msg)


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
    cols = [r[1] for r in c.execute("PRAGMA table_info(trades)").fetchall()]
    if "closed_ts" in cols and "remaining_size" in cols:
        q = "SELECT COUNT(*) FROM trades WHERE closed_ts IS NULL AND COALESCE(remaining_size,size)>0"
    elif "closed_ts" in cols:
        q = "SELECT COUNT(*) FROM trades WHERE closed_ts IS NULL"
    else:
        q = "SELECT COUNT(*) FROM trades"
    n = int(c.execute(q).fetchone()[0] or 0)
    conn.close()
    return n


def open_positions_this_round(slug: str) -> int:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    cols = [r[1] for r in c.execute("PRAGMA table_info(trades)").fetchall()]
    if "closed_ts" in cols and "remaining_size" in cols:
        c.execute("SELECT COUNT(*) FROM trades WHERE slug = ? AND closed_ts IS NULL AND COALESCE(remaining_size, size) > 0", (slug,))
    elif "closed_ts" in cols:
        c.execute("SELECT COUNT(*) FROM trades WHERE slug = ? AND closed_ts IS NULL", (slug,))
    else:
        c.execute("SELECT COUNT(*) FROM trades WHERE slug = ?", (slug,))
    n = int(c.fetchone()[0] or 0)
    conn.close()
    return n


def log_trade(slug: str, market_id: str, side: str, entry: float, size: float, edge: float, note: str, trade_token_id: str | None, entry_source: str):
    try:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute(
            "INSERT INTO trades (ts, slug, market_id, side, entry, size, edge, note, trade_token_id, entry_source, remaining_size, partial_tp_done) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now(UTC).isoformat(), slug, market_id, side, entry, size, edge, note, trade_token_id, entry_source, size, 0),
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


def maybe_auto_take_profit(slug: str, sell_yes_px: float | None, sell_no_px: float | None) -> int:
    if AUTO_TAKE_PROFIT_PCT <= 0:
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

        # 1) Mandatory partial at +30% (default)
        partial_target = entry * (1.0 + PARTIAL_TP_TRIGGER_PCT)
        if int(ptd) == 0 and close_price >= partial_target:
            qty = max(0.0, rem * max(0.0, min(1.0, PARTIAL_TP_SELL_FRACTION)))
            if qty > 0:
                pnl_partial = (float(close_price) - entry) * qty
                rem_after = max(0.0, rem - qty)
                c.execute(
                    "UPDATE trades SET remaining_size = ?, partial_tp_done = 1, close_note = ?, realized_pnl = COALESCE(realized_pnl, 0) + ? WHERE id = ?",
                    (rem_after, "partial_take_profit", float(pnl_partial), int(tid)),
                )
                net = realized_net_pnl() + pnl_partial
                side_txt = "UP" if side == "BUY_YES" else "DOWN"
                print(f"SELL TP(partial) | {side_txt} | id={tid} | sold={qty:.2f}/{rem:.2f} | pnl={pnl_partial:+.2f}")
                rem = rem_after

        # 2) Full close remainder at standard TP or absolute price target.
        tp_target = entry * (1.0 + AUTO_TAKE_PROFIT_PCT)
        abs_target_hit = (AUTO_TAKE_PROFIT_ABS > 0 and close_price >= AUTO_TAKE_PROFIT_ABS)
        if rem > 0 and (close_price >= tp_target or abs_target_hit):
            pnl = (float(close_price) - entry) * rem
            c.execute(
                "UPDATE trades SET closed_ts = ?, close_price = ?, close_note = ?, realized_pnl = COALESCE(realized_pnl, 0) + ?, remaining_size = 0 WHERE id = ?",
                (now_iso, float(close_price), "auto_take_profit", float(pnl), int(tid)),
            )
            closed += 1
            net = realized_net_pnl() + pnl
            side_txt = "UP" if side == "BUY_YES" else "DOWN"
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
        ts = datetime.fromisoformat(str(row[0]).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        age = (datetime.now(UTC) - ts).total_seconds()
        return age < STOPLOSS_REENTRY_COOLDOWN_SECONDS
    except Exception:
        return False


def parse_regime_votes(signal_text: str) -> tuple[str | None, int | None]:
    regime = None
    votes = None
    try:
        parts = [p.strip() for p in str(signal_text).split("|")]
        for p in parts:
            if p.startswith("regime="):
                regime = p.split("=", 1)[1].strip().upper()
            elif p.startswith("votes="):
                raw = p.split("=", 1)[1].strip().split("/", 1)[0]
                votes = int(raw)
    except Exception:
        return regime, votes
    return regime, votes


def has_open_opposite_side(slug: str, side: str) -> bool:
    opposite = "BUY_NO" if side == "BUY_YES" else "BUY_YES"
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    cols = [r[1] for r in c.execute("PRAGMA table_info(trades)").fetchall()]
    if "closed_ts" in cols and "remaining_size" in cols:
        q = "SELECT COUNT(*) FROM trades WHERE slug=? AND side=? AND closed_ts IS NULL AND COALESCE(remaining_size,size)>0"
    elif "closed_ts" in cols:
        q = "SELECT COUNT(*) FROM trades WHERE slug=? AND side=? AND closed_ts IS NULL"
    else:
        q = "SELECT COUNT(*) FROM trades WHERE slug=? AND side=?"
    n = int(c.execute(q, (slug, opposite)).fetchone()[0] or 0)
    conn.close()
    return n > 0


def open_same_side_count(slug: str, side: str) -> int:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    cols = [r[1] for r in c.execute("PRAGMA table_info(trades)").fetchall()]
    if "closed_ts" in cols and "remaining_size" in cols:
        q = "SELECT COUNT(*) FROM trades WHERE slug=? AND side=? AND closed_ts IS NULL AND COALESCE(remaining_size,size)>0"
    elif "closed_ts" in cols:
        q = "SELECT COUNT(*) FROM trades WHERE slug=? AND side=? AND closed_ts IS NULL"
    else:
        q = "SELECT COUNT(*) FROM trades WHERE slug=? AND side=?"
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
        last_ts = datetime.fromisoformat(str(last_ts_raw).replace("Z", "+00:00"))
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=UTC)
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


def maybe_auto_stop_loss(slug: str, eta_seconds: int | None, sell_yes_px: float | None, sell_no_px: float | None) -> int:
    if AUTO_STOP_LOSS_PCT <= 0:
        return 0
    # Apply stop logic only in final minute of the round (user preference).
    if eta_seconds is None or eta_seconds > 60:
        return 0

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    rows = c.execute(
        """
        SELECT id, ts, side, entry, COALESCE(remaining_size, size) AS size, COALESCE(partial_tp_done, 0) AS ptd
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
    for _, ts_raw, side, entry, _, ptd in rows:
        try:
            opened = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
            if opened.tzinfo is None:
                opened = opened.replace(tzinfo=UTC)
            if (now_utc - opened).total_seconds() < STOP_LOSS_ARMING_DELAY_SECONDS:
                continue
        except Exception:
            continue

        entry = float(entry)
        floor = entry * (1.0 - AUTO_STOP_LOSS_PCT)
        if BREAKEVEN_AFTER_PARTIAL and int(ptd) == 1:
            floor = max(floor, entry * (1.0 + BREAKEVEN_BUFFER_PCT))
        if side == "BUY_YES" and sell_yes_px is not None and sell_yes_px <= floor:
            stop_yes = True
        elif side == "BUY_NO" and sell_no_px is not None and sell_no_px <= floor:
            stop_no = True

    closed = 0
    now_iso = datetime.now(UTC).isoformat()
    for tid, ts_raw, side, entry, size, ptd in rows:
        if side == "BUY_YES" and not stop_yes:
            continue
        if side == "BUY_NO" and not stop_no:
            continue

        entry = float(entry)
        size = float(size)
        close_price = sell_yes_px if side == "BUY_YES" else sell_no_px
        if close_price is None:
            continue

        pnl = (float(close_price) - entry) * size
        c.execute(
            "UPDATE trades SET closed_ts = ?, close_price = ?, close_note = ?, realized_pnl = COALESCE(realized_pnl, 0) + ?, remaining_size = 0 WHERE id = ?",
            (now_iso, float(close_price), "auto_stop_loss", float(pnl), int(tid)),
        )
        closed += 1
        net = realized_net_pnl() + pnl
        side_txt = "UP" if side == "BUY_YES" else "DOWN"
        print(f"SELL SL | {side_txt} | id={tid} | pnl={pnl:+.2f}")

    conn.commit()
    conn.close()
    return closed


def maybe_auto_close_expired_round(slug: str, eta_seconds: int | None, sell_yes_px: float | None, sell_no_px: float | None) -> int:
    if eta_seconds is None or eta_seconds > 0:
        return 0

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    rows = c.execute(
        """
        SELECT id, side, entry, COALESCE(remaining_size, size) AS size
        FROM trades
        WHERE slug = ? AND closed_ts IS NULL AND COALESCE(remaining_size, size) > 0
        ORDER BY id ASC
        """,
        (slug,),
    ).fetchall()

    closed = 0
    now_iso = datetime.now(UTC).isoformat()
    for tid, side, entry, size in rows:
        entry = float(entry)
        size = float(size)
        close_price = sell_yes_px if side == "BUY_YES" else sell_no_px
        if close_price is None:
            continue
        pnl = (float(close_price) - entry) * size
        c.execute(
            "UPDATE trades SET closed_ts = ?, close_price = ?, close_note = ?, realized_pnl = COALESCE(realized_pnl, 0) + ?, remaining_size = 0 WHERE id = ?",
            (now_iso, float(close_price), "round_expired_auto_close", float(pnl), int(tid)),
        )
        closed += 1
        net = realized_net_pnl() + pnl
        side_txt = "UP" if side == "BUY_YES" else "DOWN"
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
        pnl = (float(close_price) - float(entry)) * float(size)
        c.execute(
            "UPDATE trades SET closed_ts = ?, close_price = ?, close_note = ?, realized_pnl = COALESCE(realized_pnl, 0) + ?, remaining_size = 0 WHERE id = ?",
            (datetime.now(UTC).isoformat(), float(close_price), "expired_sweep_auto_close", float(pnl), int(tid)),
        )
        closed += 1
        net = realized_net_pnl() + pnl
        print(f"ALERT EXPIRED_SWEEP_CLOSE | id={tid} slug={slug} side={side} close={float(close_price):.4f} pnl={pnl:+.2f} net_realized~={net:+.2f}")

    conn.commit()
    conn.close()
    return closed


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
            opened = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if opened.tzinfo is None:
                opened = opened.replace(tzinfo=UTC)
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
        pnl = (float(close_price) - float(entry)) * float(size)
        c.execute(
            "UPDATE trades SET closed_ts = ?, close_price = ?, close_note = ?, realized_pnl = COALESCE(realized_pnl, 0) + ?, remaining_size = 0 WHERE id = ?",
            (now.isoformat(), float(close_price), "max_hold_auto_close", float(pnl), int(tid)),
        )
        closed += 1
        net = realized_net_pnl() + pnl
        print(f"ALERT MAX_HOLD_TIMEOUT | id={tid} age={int(age)}s side={side} entry={float(entry):.4f} close={float(close_price):.4f} pnl={pnl:+.2f} net_realized~={net:+.2f}")

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
        f"sl={AUTO_STOP_LOSS_PCT:.2f} tp={AUTO_TAKE_PROFIT_PCT:.2f} partial={PARTIAL_TP_TRIGGER_PCT:.2f}/{PARTIAL_TP_SELL_FRACTION:.2f} "
        f"entries_round={MAX_ENTRIES_PER_ROUND} same_side_open_cap={MAX_SAME_SIDE_OPEN_PER_ROUND} prefixes={','.join(SERIES_PREFIXES)} max_conc={MAX_CONCURRENT_TRADES} "
        f"window={ENTRY_WINDOW_START_SECONDS}-{ENTRY_WINDOW_END_SECONDS}s loop={LOOP_SECONDS}s stop_cooldown={STOPLOSS_REENTRY_COOLDOWN_SECONDS}s"
    )

    current_force_slug = FORCE_SLUG
    last_logged_slug = None

    while True:
        try:
            maybe_close_any_expired_open_positions()
            maybe_auto_close_stale_positions()

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

                book, berr = ob.read(market.yes_token_id)
                if berr:
                    vprint(f"CANDIDATE_FAIL | prefix={pref} | slug={market.slug} | reason=clob_quote_fail")
                    continue

                spread = book.spread
                depth = book.depth_top5
                yes_bid = book.best_bid
                yes_ask = book.best_ask
                top_bid_usd = (yes_bid or 0.0) * 100.0
                top_ask_usd = (yes_ask or 0.0) * 100.0
                # Volume gate is optional; when disabled (<=0) rely on execution quality gates.
                if MIN_VOLUME24H <= 0:
                    vol_ok = True
                else:
                    vol_ok = (market.volume24h is None) or (market.volume24h >= MIN_VOLUME24H)

                gate_ok = (
                    (spread is not None and spread <= MAX_SPREAD)
                    and depth >= MIN_DEPTH_TOP5
                    and vol_ok
                )
                fail_reason = ""
                if not gate_ok:
                    if spread is None or spread > MAX_SPREAD:
                        fail_reason = "spread"
                    elif depth < MIN_DEPTH_TOP5:
                        fail_reason = "depth"
                    elif not vol_ok:
                        fail_reason = "volume24h"

                weak_top = (top_bid_usd >= MIN_TOP_BOOK_USD and top_ask_usd >= MIN_TOP_BOOK_USD)
                strong_top = (top_bid_usd >= TOP_BOOK_STRONG_USD and top_ask_usd >= TOP_BOOK_STRONG_USD)
                vprint(
                    f"CANDIDATE | engine={ENGINE_TAG} build={BUILD_TAG} | prefix={pref} slug={market.slug} suffix={market.suffix} market_id={market.market_id} "
                    f"bid={yes_bid} ask={yes_ask} spread={spread} depth={depth:.1f} top_bid_usd={top_bid_usd:.1f} top_ask_usd={top_ask_usd:.1f} "
                    f"top_bonus={'strong' if strong_top else ('weak' if weak_top else 'none')} vol24h={market.volume24h} gate={gate_ok} reason={fail_reason or 'ok'}"
                )

                if gate_ok:
                    in_band = (BUY_YES_MIN_ENTRY <= (yes_ask or market.yes_price) < BUY_YES_MAX_ENTRY) or (
                        BUY_NO_MIN_ENTRY <= (1.0 - (yes_bid or market.yes_price)) < BUY_NO_MAX_ENTRY
                    )
                    score = candidate_score(spread, depth, book.imbalance, in_band, top_bid_usd, top_ask_usd)
                    candidates.append((score, pref, market, book))

            if not candidates:
                time.sleep(LOOP_SECONDS)
                continue

            candidates.sort(key=lambda x: x[0], reverse=True)
            available_slots = max(0, MAX_CONCURRENT_TRADES - open_positions_total())
            if available_slots <= 0:
                vprint(f"SELECTED | n=0 reason=no_available_slots max_concurrent={MAX_CONCURRENT_TRADES}")
                time.sleep(LOOP_SECONDS)
                continue

            selected = []
            used_keys = set()
            for score, pref, mkt, bok in candidates:
                key = (pref, mkt.suffix)
                if key in used_keys:
                    continue
                if trades_taken_on_slug(mkt.slug) >= MAX_TRADES_PER_SLUG:
                    continue
                selected.append((score, pref, mkt, bok))
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
            _, chosen_prefix, market, book = selected[0]

            if market.slug != last_logged_slug:
                print(
                    f"Market selected | prefix={chosen_prefix} | slug={market.slug} | suffix={market.suffix} | market_id={market.market_id} "
                    f"| yes_token_id={market.yes_token_id} | no_token_id={market.no_token_id}"
                )
                last_logged_slug = market.slug

            prob, stext, serr = signal_up_prob()
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

            buy_yes_px = yes_best_ask if yes_best_ask is not None else market.yes_price
            buy_no_px = (1.0 - yes_best_bid) if yes_best_bid is not None else market.no_price
            sell_yes_px = yes_best_bid if yes_best_bid is not None else market.yes_price
            sell_no_px = (1.0 - yes_best_ask) if yes_best_ask is not None else market.no_price

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
            maybe_auto_close_expired_round(market.slug, eta_now, sell_yes_px, sell_no_px)
            maybe_auto_group_take_profit(market.slug, sell_yes_px, sell_no_px)
            maybe_auto_take_profit(market.slug, sell_yes_px, sell_no_px)
            maybe_auto_stop_loss(market.slug, eta_now, sell_yes_px, sell_no_px)

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
            edge_yes = prob - buy_yes_px
            edge_no = (1.0 - prob) - buy_no_px

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
            if STRONG_REGIME_ONLY and regime is not None and votes is not None:
                long_allowed = (regime == "BULL" and votes >= BULL_MIN_VOTES)
                short_allowed = (regime == "BEAR" and votes <= BEAR_MAX_VOTES)

            side_yes_min_edge = MIN_EDGE
            side_no_min_edge = MIN_EDGE
            yes_recent = recent_side_realized_pnl("BUY_YES", SIDE_PERF_LOOKBACK)
            no_recent = recent_side_realized_pnl("BUY_NO", SIDE_PERF_LOOKBACK)
            if yes_recent < 0:
                side_yes_min_edge += LOSING_SIDE_EDGE_PENALTY
            if no_recent < 0:
                side_no_min_edge += LOSING_SIDE_EDGE_PENALTY

            yes_ok = edge_yes >= side_yes_min_edge and long_allowed
            no_ok = edge_no >= side_no_min_edge and short_allowed

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
            if yes_ok and no_ok and abs(edge_yes - edge_no) < MIN_SIDE_ADVANTAGE:
                print(
                    f"No trade | side advantage too small (edge_yes={edge_yes:.4f}, edge_no={edge_no:.4f}, min={MIN_SIDE_ADVANTAGE:.4f})"
                )
                time.sleep(LOOP_SECONDS)
                continue

            prefer_yes = prob > 0.5
            prefer_no = prob < 0.5

            if prefer_yes and yes_ok and (not no_ok or edge_yes >= edge_no):
                side = "BUY_YES"
                entry = buy_yes_px
                edge = edge_yes
                trade_token_id = market.yes_token_id
                entry_source = "clob" if yes_best_ask is not None else "gamma"
            elif prefer_no and no_ok and (not yes_ok or edge_no >= edge_yes):
                side = "BUY_NO"
                entry = buy_no_px
                edge = edge_no
                trade_token_id = market.no_token_id
                entry_source = "clob" if yes_best_bid is not None else "gamma"

            if not side:
                regime_txt = f"regime={regime} votes={votes}" if regime is not None else "regime=n/a"
                print(
                    f"No trade | edge_yes={edge_yes:.4f} edge_no={edge_no:.4f} "
                    f"| fair_yes<= {yes_fair_limit:.3f} fair_no<= {no_fair_limit:.3f} "
                    f"| {regime_txt}"
                )
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
            size = risk / max(entry, 1e-6)
            note = (
                f"edge={edge:.4f} spread={spread} depth={depth:.1f} imbalance={imbalance:.2f} "
                f"source={entry_source} bal={balance_now:.2f} risk={risk:.2f} mult={risk_mult:.2f}"
            )
            log_trade(market.slug, market.market_id, side, entry, size, edge, note, trade_token_id, entry_source)
            side_txt = "UP" if side == "BUY_YES" else "DOWN"
            print(f"BUY {side_txt} | entry={entry:.4f} | size={size:.2f}")

            time.sleep(LOOP_SECONDS)
        except KeyboardInterrupt:
            print("Stopping V4.")
            break
        except Exception as e:
            print(f"[ERR 1999] loop_error: {e}")
            time.sleep(LOOP_SECONDS)


if __name__ == "__main__":
    main()


