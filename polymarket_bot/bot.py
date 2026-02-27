import os
import time
import json
import re
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime, date, UTC

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False

from data_client import MarketClient
from strategy import fair_probability, should_buy_yes, should_buy_no
from btc_signal import get_btc_signal_prob
from clob_discovery import discover_latest_btc_5m_slug


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
MAX_ENTRIES_PER_MARKET_PER_DAY = _env_int("MAX_ENTRIES_PER_MARKET_PER_DAY", 3)
REENTRY_COOLDOWN_SECONDS = _env_int("REENTRY_COOLDOWN_SECONDS", 20)
MIN_EDGE = _env_float("MIN_EDGE", 0.04)
MIN_MODEL_CONFIDENCE = _env_float("MIN_MODEL_CONFIDENCE", 0.05)
TIERED_ENTRY_MODE = os.getenv("TIERED_ENTRY_MODE", "true").lower() == "true"
PROBE_EDGE = _env_float("PROBE_EDGE", 0.15)
PROBE_RISK_PCT = _env_float("PROBE_RISK_PCT", 0.002)
CONFIRM_RISK_PCT = _env_float("CONFIRM_RISK_PCT", 0.003)
MIN_PRICE = _env_float("MIN_PRICE", 0.05)
MAX_PRICE = _env_float("MAX_PRICE", 0.85)
BTC_ONLY = os.getenv("BTC_ONLY", "true").lower() == "true"
BTC_FOCUS_MODE = os.getenv("BTC_FOCUS_MODE", "ultrashort").lower()  # ultrashort|any
FORCE_MARKET_IDS = {x.strip() for x in os.getenv("FORCE_MARKET_IDS", "").split(",") if x.strip()}
FORCE_MARKET_SLUG_CONTAINS = os.getenv("FORCE_MARKET_SLUG_CONTAINS", "").strip().lower()
AUTO_BTC_5M_CLOB_DISCOVERY = os.getenv("AUTO_BTC_5M_CLOB_DISCOVERY", "true").lower() == "true"
AUTO_FORCE_SLUG_STEP = os.getenv("AUTO_FORCE_SLUG_STEP", "true").lower() == "true"
ALIGN_STEP_TO_CLOCK = os.getenv("ALIGN_STEP_TO_CLOCK", "true").lower() == "true"
AUTO_SLUG_FROM_URL = os.getenv("AUTO_SLUG_FROM_URL", "true").lower() == "true"
CURRENT_EVENT_URL = os.getenv("CURRENT_EVENT_URL", "").strip()
ROUND_MINUTES = _env_int("ROUND_MINUTES", 5)
SERIES_PREFIX = os.getenv("SERIES_PREFIX", "btc-updown").lower()
DEBUG_CANDIDATES = os.getenv("DEBUG_CANDIDATES", "true").lower() == "true"
ENABLE_SLUG_PROMPT = os.getenv("ENABLE_SLUG_PROMPT", "true").lower() == "true"
STEP_ON_MISS = os.getenv("STEP_ON_MISS", "true").lower() == "true"
MAX_HOPS_ON_MISS = _env_int("MAX_HOPS_ON_MISS", 2)
FORCE_SLUG_STEP_SIZE = _env_int("FORCE_SLUG_STEP_SIZE", 300)
FORCE_SLUG_STEP_SECONDS = _env_int("FORCE_SLUG_STEP_SECONDS", 300)
MIN_SECONDS_TO_EXPIRY = _env_int("MIN_SECONDS_TO_EXPIRY", 20)
LOOP_SECONDS = _env_int("LOOP_SECONDS", 60)
AUTO_TAKE_PROFIT_PCT = _env_float("AUTO_TAKE_PROFIT_PCT", 0.25)
AUTO_REENTER_AFTER_CASHOUT = os.getenv("AUTO_REENTER_AFTER_CASHOUT", "true").lower() == "true"
DB_PATH = "trades.db"
FORCE_SLUG_STATE_FILE = Path("force_slug_state.json")
CASHOUT_ARCHIVE_DIR = Path("cashout_archive")
EXPIRY_SPAM_STATE_FILE = Path("expiry_spam_state.json")

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


def entries_for_market_side_today(market_id: str, side: str = "BUY_YES") -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    today = date.today().isoformat()
    cur.execute(
        "SELECT COUNT(*) FROM trades WHERE market_id = ? AND side = ? AND ts LIKE ?",
        (market_id, side, f"{today}%"),
    )
    cnt = int(cur.fetchone()[0] or 0)
    conn.close()
    return cnt


def cooldown_ready(market_id: str, side: str = "BUY_YES") -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    today = date.today().isoformat()
    cur.execute(
        "SELECT ts FROM trades WHERE market_id = ? AND side = ? AND ts LIKE ? ORDER BY id DESC LIMIT 1",
        (market_id, side, f"{today}%"),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return True
    try:
        last_ts = datetime.fromisoformat(str(row[0]))
        return (datetime.now(UTC) - last_ts).total_seconds() >= REENTRY_COOLDOWN_SECONDS
    except Exception:
        return True


def trades_count_today() -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    today = date.today().isoformat()
    cur.execute("SELECT COUNT(*) FROM trades WHERE ts LIKE ?", (f"{today}%",))
    val = int(cur.fetchone()[0] or 0)
    conn.close()
    return val


def max_position_size(bankroll: float, price: float, risk_pct: float | None = None) -> float:
    rp = MAX_RISK_PER_TRADE_PCT if risk_pct is None else max(0.0, risk_pct)
    risk_dollars = bankroll * rp
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
        yes_now = max(0.0, min(1.0, float(current_price)))

        if side == "BUY_YES":
            raw = (yes_now - entry_price) * size
            min_loss = -entry_price * size
            max_gain = (1.0 - entry_price) * size
            pnl += max(min(raw, max_gain), min_loss)
        elif side == "BUY_NO":
            # NO contract value = 1 - YES price
            no_now = 1.0 - yes_now
            raw = (no_now - entry_price) * size
            min_loss = -entry_price * size
            max_gain = (1.0 - entry_price) * size
            pnl += max(min(raw, max_gain), min_loss)
    return pnl


def position_snapshot(market_prices: dict[str, float], limit: int = 3) -> list[tuple[str, str, float]]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT market_id, side, price, size FROM trades WHERE side IN ('BUY_YES','BUY_NO')")
    rows = cur.fetchall()
    conn.close()

    agg: dict[str, dict] = {}
    for market_id, side, price, size in rows:
        key = f"{market_id}:{side}"
        if key not in agg:
            agg[key] = {"market_id": str(market_id), "side": side, "qty": 0.0, "cost": 0.0}
        agg[key]["qty"] += float(size)
        agg[key]["cost"] += float(price) * float(size)

    out = []
    for _, p in agg.items():
        yes_now = market_prices.get(p["market_id"])
        if yes_now is None:
            continue
        qty = p["qty"]
        entry = (p["cost"] / qty) if qty else 0.0
        curr = yes_now if p["side"] == "BUY_YES" else (1.0 - yes_now)
        pnl = (curr - entry) * qty
        out.append((p["market_id"], p["side"], pnl))

    out.sort(key=lambda x: x[2], reverse=True)
    return out[:limit]


def entry_snapshot(market_prices: dict[str, float], limit: int = 8) -> list[tuple[str, str, float, float, float]]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, market_id, side, price, size FROM trades WHERE side IN ('BUY_YES','BUY_NO') ORDER BY id DESC"
    )
    rows = cur.fetchall()
    conn.close()

    out = []
    for _, market_id, side, price, size in rows:
        yes_now = market_prices.get(str(market_id))
        if yes_now is None:
            continue
        entry = float(price)
        qty = float(size)
        curr = yes_now if side == "BUY_YES" else (1.0 - yes_now)
        pnl = (curr - entry) * qty
        out.append((str(market_id), side, entry, qty, pnl))
        if len(out) >= limit:
            break
    return out


def maybe_auto_cashout(market_prices: dict[str, float]) -> tuple[bool, float]:
    notional = today_trade_notional()
    if notional <= 0:
        return False, 0.0

    pnl_now = unrealized_pnl(market_prices)
    target = notional * AUTO_TAKE_PROFIT_PCT
    if pnl_now < target:
        return False, pnl_now

    # Archive and reset DB as a paper "cash out"
    CASHOUT_ARCHIVE_DIR.mkdir(exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    archived = CASHOUT_ARCHIVE_DIR / f"trades_{ts}.db"
    try:
        if Path(DB_PATH).exists():
            shutil.copy2(DB_PATH, archived)
            Path(DB_PATH).unlink(missing_ok=True)
        init_db()
        print(f"💰 Auto-cashout hit ({AUTO_TAKE_PROFIT_PCT*100:.0f}% target): {color_pnl(pnl_now)} | archived -> {archived}", flush=True)
        return True, pnl_now
    except Exception as e:
        print(f"Cashout error: {e}", flush=True)
        return False, pnl_now


def is_ultrashort_btc_market(question_lower: str) -> bool:
    minute_token = f"{ROUND_MINUTES}m"
    minute_hint = (minute_token in question_lower) or (f"{ROUND_MINUTES} min" in question_lower) or (f"{ROUND_MINUTES}-minute" in question_lower) or (f"{ROUND_MINUTES} minute" in question_lower)
    updown_hint = ("up or down" in question_lower) or ("higher or lower" in question_lower)
    return minute_hint and updown_hint


def _infer_up_is_yes(outcomes: list[str] | None) -> bool:
    if not outcomes or len(outcomes) < 2:
        return True
    o0 = str(outcomes[0]).lower()
    o1 = str(outcomes[1]).lower()

    def is_up(x: str) -> bool:
        return ("up" in x) or ("higher" in x) or (x.strip() == "yes")

    if is_up(o0):
        return True
    if is_up(o1):
        return False
    return True


def _step_slug(slug: str, step: int) -> str | None:
    m = re.search(r"(.*-)(\d+)$", slug)
    if not m:
        return None
    base, n = m.group(1), int(m.group(2))
    return f"{base}{n + step}"


def _seconds_left_from_slug(slug: str | None) -> int | None:
    if not slug:
        return None

    s = str(slug).lower()
    # Only trust slug-clock timing for expected series format, e.g. btc-updown-15m-1772230500
    m = re.search(rf"{re.escape('btc-updown')}-{ROUND_MINUTES}m-(\d{{10}})$", s)
    if not m:
        return None

    try:
        start_ts = int(m.group(1))
        # Sanity guard for unix epoch seconds (avoid interpreting ids like 644395 as timestamps)
        if start_ts < 1_600_000_000:
            return None
        end_ts = start_ts + (ROUND_MINUTES * 60)
        return end_ts - int(time.time())
    except Exception:
        return None


def _align_slug_to_current_round(slug: str | None) -> str | None:
    if not slug:
        return None
    m = re.search(r"(.*-)(\d+)$", str(slug))
    if not m:
        return None
    prefix = m.group(1)
    now_ts = int(time.time())
    interval = max(60, ROUND_MINUTES * 60)
    round_start = (now_ts // interval) * interval
    return f"{prefix}{round_start}"


def _slug_from_event_url(url: str | None) -> str | None:
    if not url:
        return None

    pat = rf"/event/(btc-updown-{ROUND_MINUTES}m-\d+)"

    # 1) direct parse from provided URL
    m = re.search(pat, str(url).lower())
    if m:
        return m.group(1)

    # 2) resolve/refresh URL (handles redirects to current round)
    try:
        r = requests.get(url, timeout=8, allow_redirects=True)
        final_url = str(r.url).lower()
        m2 = re.search(pat, final_url)
        if m2:
            return m2.group(1)
    except Exception:
        pass

    return None


def _prompt_slug_override(current_slug: str) -> str:
    if not ENABLE_SLUG_PROMPT:
        return current_slug
    try:
        suffix = input("Enter current slug suffix now (example: 1772230800). Press Enter to keep current: ").strip()
    except Exception:
        return current_slug

    if not suffix:
        return current_slug
    if not suffix.isdigit() or len(suffix) < 9:
        print("Invalid suffix; keeping current slug.", flush=True)
        return current_slug

    return f"{SERIES_PREFIX}-{ROUND_MINUTES}m-{suffix}"


def _load_force_state(default_slug: str) -> dict:
    if FORCE_SLUG_STATE_FILE.exists():
        try:
            return json.loads(FORCE_SLUG_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"slug": default_slug, "last_step_ts": 0, "last_clock_bucket": -1}


def _save_force_state(state: dict):
    try:
        FORCE_SLUG_STATE_FILE.write_text(json.dumps(state), encoding="utf-8")
    except Exception:
        pass


def _load_expiry_spam_state() -> dict:
    if EXPIRY_SPAM_STATE_FILE.exists():
        try:
            return json.loads(EXPIRY_SPAM_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_expiry_spam_state(state: dict):
    try:
        EXPIRY_SPAM_STATE_FILE.write_text(json.dumps(state), encoding="utf-8")
    except Exception:
        pass


def maybe_auto_step_force_slug(current_slug: str) -> tuple[str, int | None]:
    if not AUTO_FORCE_SLUG_STEP or not current_slug:
        return current_slug, None

    state = _load_force_state(current_slug)
    now_ts = int(time.time())

    # If env slug changed manually, sync state immediately.
    if state.get("slug") != current_slug:
        state["slug"] = current_slug
        state["last_step_ts"] = now_ts
        state["last_clock_bucket"] = now_ts // max(1, FORCE_SLUG_STEP_SECONDS)
        _save_force_state(state)

    if ALIGN_STEP_TO_CLOCK:
        interval = max(1, FORCE_SLUG_STEP_SECONDS)
        current_bucket = now_ts // interval
        last_bucket = int(state.get("last_clock_bucket", -1))

        # Step once per new wall-clock bucket
        if last_bucket >= 0 and current_bucket > last_bucket:
            next_slug = _step_slug(current_slug, FORCE_SLUG_STEP_SIZE)
            if next_slug:
                state["slug"] = next_slug
                state["last_step_ts"] = now_ts
                state["last_clock_bucket"] = current_bucket
                _save_force_state(state)
                print(f"Clock-aligned step: force slug -> {next_slug}", flush=True)
                # time until next boundary
                eta = interval - (now_ts % interval)
                return next_slug, eta

        # no step yet: show ETA to boundary
        eta = interval - (now_ts % interval)
        state["last_clock_bucket"] = current_bucket
        _save_force_state(state)
        return current_slug, eta

    # Legacy elapsed-timer stepping
    last_ts = int(state.get("last_step_ts", 0))
    elapsed = now_ts - last_ts
    if elapsed < FORCE_SLUG_STEP_SECONDS:
        return current_slug, max(0, FORCE_SLUG_STEP_SECONDS - elapsed)

    next_slug = _step_slug(current_slug, FORCE_SLUG_STEP_SIZE)
    if next_slug:
        state["slug"] = next_slug
        state["last_step_ts"] = now_ts
        _save_force_state(state)
        print(f"Clock step: force slug -> {next_slug}", flush=True)
        return next_slug, FORCE_SLUG_STEP_SECONDS

    return current_slug, None


def main():
    init_db()
    client = MarketClient()
    bankroll = STARTING_BANKROLL

    runtime_force_slug = FORCE_MARKET_SLUG_CONTAINS
    runtime_force_slug = _prompt_slug_override(runtime_force_slug)

    print("=" * 72, flush=True)
    print("🚀 POLYMARKET PAPER BOT", flush=True)
    print(f"Mode: {'PAPER' if PAPER_MODE else 'LIVE'} | Bankroll: ${bankroll:.2f}", flush=True)
    print("=" * 72, flush=True)

    while True:
        try:
            daily_cap = bankroll * MAX_DAILY_DRAWDOWN_PCT
            spent_today = today_trade_notional()
            trade_count = trades_count_today()

            if spent_today >= daily_cap or trade_count >= MAX_TRADES_PER_DAY:
                cap_reason = "risk" if spent_today >= daily_cap else "trade-count"
                print(f"⏸️ Cap reached ({cap_reason}). Monitor mode...", flush=True)

                markets = client.fetch_markets()
                market_prices = {str(m.market_id): float(m.yes_price) for m in markets}
                mtm = unrealized_pnl(market_prices)
                pnl_colored = color_pnl(mtm)
                print(
                    f"📊 Status | trades: {trade_count}/{MAX_TRADES_PER_DAY} | notional: ${spent_today:.2f} | unrealized: {pnl_colored}",
                    flush=True,
                )
                top_positions = position_snapshot(market_prices, limit=3)
                if top_positions:
                    print("📌 Top positions (best→worst):", flush=True)
                    for mid, side, p in top_positions:
                        print(f"   {mid} [{side}] {color_pnl(p)}", flush=True)

                entries = entry_snapshot(market_prices, limit=8)
                if entries:
                    print("🧾 Entries (latest):", flush=True)
                    for mid, side, entry, qty, pnl in entries:
                        print(f"   {mid} [{side}] entry={entry:.4f} size={qty:.2f} pnl={color_pnl(pnl)}", flush=True)
                print("-" * 72, flush=True)

                time.sleep(LOOP_SECONDS)
                continue

            markets = client.fetch_markets()
            print(f"\n🧭 Scan | Active markets: {len(markets)}", flush=True)
            market_prices = {str(m.market_id): float(m.yes_price) for m in markets}

            if DEBUG_CANDIDATES:
                token = f"{SERIES_PREFIX}-{ROUND_MINUTES}m"
                cands = [m.slug for m in markets if m.slug and token in m.slug.lower()]
                if cands:
                    print(f"🔎 Candidate slugs ({token}): {', '.join(cands[:3])}", flush=True)
                else:
                    print(f"🔎 Candidate slugs ({token}): none", flush=True)

            btc_prob = None
            btc_reason = ""
            if BTC_ONLY:
                btc_prob, btc_reason = get_btc_signal_prob()
                print(f"₿ Signal | {btc_reason}", flush=True)

            base_force_slug = runtime_force_slug
            if AUTO_SLUG_FROM_URL and CURRENT_EVENT_URL:
                slug_from_url = _slug_from_event_url(CURRENT_EVENT_URL)
                if slug_from_url:
                    base_force_slug = slug_from_url

            active_force_slug, step_eta = maybe_auto_step_force_slug(base_force_slug)
            runtime_force_slug = active_force_slug or runtime_force_slug
            slug_changed_this_loop = False
            if step_eta is not None:
                print(f"⏱️ Next slug step in: {step_eta}s", flush=True)

            if AUTO_BTC_5M_CLOB_DISCOVERY and not active_force_slug:
                discovered_slug, reason = discover_latest_btc_5m_slug()
                if discovered_slug:
                    active_force_slug = discovered_slug.lower()
                print(f"CLOB discovery: {reason} slug={discovered_slug}", flush=True)

            if active_force_slug:
                forced_hits = 0
                for m in markets:
                    m_slug = (m.slug or "").lower()
                    if active_force_slug in m_slug:
                        forced_hits += 1

                if forced_hits == 0 and AUTO_FORCE_SLUG_STEP:
                    max_hops = 12
                    candidate = active_force_slug
                    for hop in range(1, max_hops + 1):
                        stepped = _step_slug(candidate, FORCE_SLUG_STEP_SIZE)
                        if not stepped:
                            break
                        stepped = stepped.lower()

                        stepped_hits = 0
                        for m in markets:
                            m_slug = (m.slug or "").lower()
                            if stepped in m_slug:
                                stepped_hits += 1

                        if stepped_hits > 0:
                            active_force_slug = stepped
                            slug_changed_this_loop = True
                            state = _load_force_state(active_force_slug)
                            state["slug"] = active_force_slug
                            state["last_step_ts"] = int(time.time())
                            _save_force_state(state)
                            print(
                                f"Force slug miss -> hopped +{FORCE_SLUG_STEP_SIZE} x{hop} and matched: '{active_force_slug}'",
                                flush=True,
                            )
                            forced_hits = stepped_hits
                            break

                        candidate = stepped

                    # Fallback: if a single BTC 5m market is visible, lock onto its actual slug directly.
                    if forced_hits == 0:
                        btc5_slugs = []
                        for m in markets:
                            m_slug = (m.slug or "").lower()
                            q = (m.question or "").lower()
                            if ("btc-updown-5m" in m_slug) or ("bitcoin" in q and "up or down" in q and "5" in q):
                                btc5_slugs.append(m_slug)
                        if len(btc5_slugs) == 1 and btc5_slugs[0]:
                            active_force_slug = btc5_slugs[0]
                            slug_changed_this_loop = True
                            state = _load_force_state(active_force_slug)
                            state["slug"] = active_force_slug
                            state["last_step_ts"] = int(time.time())
                            _save_force_state(state)
                            print(f"Force slug miss -> adopted visible btc5 slug: '{active_force_slug}'", flush=True)
                            forced_hits = 1

                if forced_hits == 0:
                    # On miss, do NOT keep hopping ahead; hold current target slug and wait.
                    if forced_hits == 0:
                        if STEP_ON_MISS and AUTO_FORCE_SLUG_STEP and active_force_slug:
                            candidate = active_force_slug
                            for hop in range(1, max(1, MAX_HOPS_ON_MISS) + 1):
                                stepped = _step_slug(candidate, FORCE_SLUG_STEP_SIZE)
                                if not stepped:
                                    break
                                candidate = stepped.lower()
                                print(f"Force slug miss -> advanced +{FORCE_SLUG_STEP_SIZE} x{hop} to '{candidate}'", flush=True)
                            active_force_slug = candidate
                            state = _load_force_state(active_force_slug)
                            state["slug"] = active_force_slug
                            state["last_step_ts"] = int(time.time())
                            _save_force_state(state)

                        print(
                            f"Force slug '{active_force_slug}' not present in fetched markets; waiting for correct round (no fallback trades).",
                            flush=True,
                        )
                        print("-" * 72, flush=True)
                        time.sleep(LOOP_SECONDS)
                        continue

            if slug_changed_this_loop:
                runtime_force_slug = active_force_slug or runtime_force_slug
                print("🔄 New slug established; resetting expiry checks on next scan.", flush=True)
                print("-" * 72, flush=True)
                time.sleep(LOOP_SECONDS)
                continue

            runtime_force_slug = active_force_slug or runtime_force_slug
            skip_forced_market = 0
            skip_non_btc = 0
            skip_signal_unavailable = 0
            skip_price = 0
            skip_edge = 0
            skip_near_expiry = 0
            slug_advanced_on_expiry = False
            trades_placed_this_loop = 0

            for m in markets:
                if FORCE_MARKET_IDS and str(m.market_id) not in FORCE_MARKET_IDS:
                    skip_forced_market += 1
                    continue

                if active_force_slug:
                    m_slug = (m.slug or "").lower()
                    if active_force_slug not in m_slug:
                        skip_forced_market += 1
                        continue

                # Skip stale/almost-finished rounds so we don't trade prior event windows.
                # Prefer slug-clock (more reliable for btc-updown-5m) over API end_date.
                seconds_left = _seconds_left_from_slug(m.slug)
                if seconds_left is None and m.end_date:
                    try:
                        end_dt = datetime.fromisoformat(str(m.end_date).replace("Z", "+00:00"))
                        seconds_left = int((end_dt - datetime.now(UTC)).total_seconds())
                    except Exception:
                        seconds_left = None

                if seconds_left is not None and seconds_left <= MIN_SECONDS_TO_EXPIRY:
                    skip_near_expiry += 1
                    spam_state = _load_expiry_spam_state()
                    spam_key = f"{active_force_slug}:{m.market_id}"
                    if spam_state.get("last") != spam_key:
                        print(
                            f"Expiry gate | market={m.market_id} seconds_left={seconds_left} min_required>{MIN_SECONDS_TO_EXPIRY}",
                            flush=True,
                        )
                        spam_state["last"] = spam_key
                        _save_expiry_spam_state(spam_state)

                    # If forced slug is clearly stale, auto-jump to next slug immediately.
                    if (
                        AUTO_FORCE_SLUG_STEP
                        and active_force_slug
                        and (seconds_left < -5)
                        and not slug_advanced_on_expiry
                    ):
                        aligned_slug = _align_slug_to_current_round(active_force_slug)
                        next_slug = aligned_slug or _step_slug(active_force_slug, FORCE_SLUG_STEP_SIZE)
                        if next_slug and next_slug.lower() == active_force_slug:
                            next_slug = _step_slug(active_force_slug, FORCE_SLUG_STEP_SIZE)

                        if next_slug:
                            active_force_slug = next_slug.lower()
                            state = _load_force_state(active_force_slug)
                            state["slug"] = active_force_slug
                            state["last_step_ts"] = int(time.time())
                            _save_force_state(state)
                            slug_advanced_on_expiry = True
                            slug_changed_this_loop = True
                            print(f"⏩ Expired round detected -> jumped to current round slug {active_force_slug}", flush=True)
                            _save_expiry_spam_state({})
                            # Stop processing stale rows immediately; next loop will re-scan with new slug.
                            break
                    continue

                # Hard market-price filters to avoid tiny-price spam buys
                if m.yes_price < MIN_PRICE or m.yes_price > MAX_PRICE:
                    skip_price += 1
                    continue

                q_lower = m.question.lower()
                slug_lower = (m.slug or "").lower()
                is_btc_market = ("btc" in q_lower) or ("bitcoin" in q_lower) or ("btc" in slug_lower) or ("bitcoin" in slug_lower)

                if BTC_ONLY and not active_force_slug and not is_btc_market:
                    skip_non_btc += 1
                    continue

                if BTC_ONLY and BTC_FOCUS_MODE == "ultrashort" and not active_force_slug and not is_ultrashort_btc_market(q_lower):
                    skip_non_btc += 1
                    continue

                if BTC_ONLY:
                    if btc_prob is None:
                        skip_signal_unavailable += 1
                        continue
                    model_prob = fair_probability(btc_prob)
                else:
                    model_prob = fair_probability(m.signal_prob)

                # Confidence gate: skip weak near-50/50 signals
                if abs(model_prob - 0.5) < MIN_MODEL_CONFIDENCE:
                    skip_edge += 1
                    continue

                up_is_yes = _infer_up_is_yes(m.outcomes)
                market_up_price = m.yes_price if up_is_yes else (1.0 - m.yes_price)

                buy_side = None
                edge_val = 0.0
                if should_buy_yes(market_up_price, model_prob, MIN_EDGE):
                    # Bullish bet -> BUY_YES if outcome0 is Up, else BUY_NO
                    buy_side = "BUY_YES" if up_is_yes else "BUY_NO"
                    edge_val = model_prob - market_up_price
                elif should_buy_no(market_up_price, model_prob, MIN_EDGE):
                    # Bearish bet -> BUY_NO if outcome0 is Up, else BUY_YES
                    buy_side = "BUY_NO" if up_is_yes else "BUY_YES"
                    edge_val = market_up_price - model_prob
                else:
                    skip_edge += 1

                if buy_side:
                    entries_today_side = entries_for_market_side_today(m.market_id, buy_side)
                    if entries_today_side >= MAX_ENTRIES_PER_MARKET_PER_DAY:
                        continue
                    if not cooldown_ready(m.market_id, buy_side):
                        continue

                    # Recheck caps before each order
                    spent_today = today_trade_notional()
                    trade_count = trades_count_today()
                    if spent_today >= daily_cap or trade_count >= MAX_TRADES_PER_DAY:
                        print("In-loop cap reached. Stopping new trades this cycle.", flush=True)
                        break

                    # NO price is inverse of YES price
                    entry_price = m.yes_price if buy_side == "BUY_YES" else (1.0 - m.yes_price)

                    # Tiered sizing: small probe on extreme edge, larger confirm add-on.
                    risk_pct = MAX_RISK_PER_TRADE_PCT
                    tier_tag = "base"
                    if TIERED_ENTRY_MODE:
                        if entries_today_side == 0 and edge_val >= PROBE_EDGE:
                            risk_pct = PROBE_RISK_PCT
                            tier_tag = "probe"
                        elif entries_today_side >= 1 and edge_val >= MIN_EDGE:
                            risk_pct = CONFIRM_RISK_PCT
                            tier_tag = "confirm"
                        elif entries_today_side == 0:
                            # no probe unless dislocation is large
                            continue

                    size = max_position_size(bankroll, entry_price, risk_pct=risk_pct)
                    if size <= 0:
                        continue

                    mode = "paper" if PAPER_MODE else "live"
                    outcomes_txt = "/".join(m.outcomes) if m.outcomes else "n/a"
                    map_txt = f"up_is_{'YES' if up_is_yes else 'NO'}"
                    note = f"edge={round(edge_val, 4)} tier={tier_tag} risk_pct={risk_pct:.4f} {map_txt} outcomes={outcomes_txt}"
                    log_trade(m.market_id, m.question, buy_side, entry_price, size, mode, note)
                    trades_placed_this_loop += 1
                    side_emoji = "🟢" if buy_side == "BUY_YES" else "🔴"
                    print(f"{side_emoji} Trade | {buy_side} | market={m.market_id} | entry={entry_price:.4f} | size={size:.4f} | {note}", flush=True)

            if slug_advanced_on_expiry:
                print("🔄 Expired slug advanced; re-scanning next loop before new entries.", flush=True)
                print("-" * 72, flush=True)
                time.sleep(LOOP_SECONDS)
                continue

            print(
                f"🧪 Debug | placed={trades_placed_this_loop} | skip_forced={skip_forced_market} | skip_non_btc={skip_non_btc} | skip_signal={skip_signal_unavailable} | skip_near_expiry={skip_near_expiry} | skip_price={skip_price} | skip_edge={skip_edge}",
                flush=True,
            )

            trades_today = trades_count_today()
            notional_today = today_trade_notional()
            mtm = unrealized_pnl(market_prices)
            pnl_colored = color_pnl(mtm)
            print(
                f"📊 Status | trades: {trades_today}/{MAX_TRADES_PER_DAY} | notional: ${notional_today:.2f} | unrealized: {pnl_colored}",
                flush=True,
            )

            cashed_out, pnl_now = maybe_auto_cashout(market_prices)
            if cashed_out and AUTO_REENTER_AFTER_CASHOUT:
                print("🔁 Re-enter mode: ready for next setups after cashout.", flush=True)

            top_positions = position_snapshot(market_prices, limit=3)
            if top_positions:
                print("📌 Top positions (best→worst):", flush=True)
                for mid, side, p in top_positions:
                    print(f"   {mid} [{side}] {color_pnl(p)}", flush=True)

            entries = entry_snapshot(market_prices, limit=8)
            if entries:
                print("🧾 Entries (latest):", flush=True)
                for mid, side, entry, qty, pnl in entries:
                    print(f"   {mid} [{side}] entry={entry:.4f} size={qty:.2f} pnl={color_pnl(pnl)}", flush=True)

            print("-" * 72, flush=True)

            time.sleep(LOOP_SECONDS)

        except KeyboardInterrupt:
            print("Stopping bot.")
            break
        except Exception as e:
            print(f"Loop error: {e}", flush=True)
            time.sleep(LOOP_SECONDS)


if __name__ == "__main__":
    main()
