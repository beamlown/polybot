from datetime import datetime
from pathlib import Path
from typing import Optional
import os
import re

import requests
from py_clob_client.client import ClobClient


HOST = "https://clob.polymarket.com"
CHAIN_ID = 137
GAMMA = "https://gamma-api.polymarket.com"
STATE_FILE = Path(__file__).parent / "last_btc_5m_slug.txt"


def _parse_dt(dt_str: str | None) -> datetime:
    if not dt_str:
        return datetime.min
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return datetime.min


def _is_btc_5m_market(m: dict) -> bool:
    slug = str(m.get("market_slug") or "").lower()
    question = str(m.get("question") or "").lower()

    if "btc-updown-5m" in slug:
        return True

    has_btc = ("btc" in slug) or ("bitcoin" in question)
    has_updown = ("up or down" in question) or ("higher or lower" in question)
    has_5m = ("5m" in slug) or ("5 min" in question) or ("5-minute" in question) or ("5 minute" in question)
    return has_btc and has_updown and has_5m


def _save_last_slug(slug: str):
    try:
        STATE_FILE.write_text(slug.strip(), encoding="utf-8")
    except Exception:
        pass


def _load_last_slug() -> str:
    hint = os.getenv("LAST_BTC_5M_SLUG_HINT", "").strip()
    if hint:
        return hint
    try:
        if STATE_FILE.exists():
            return STATE_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return ""


def _slug_exists_active(slug: str) -> bool:
    try:
        resp = requests.get(f"{GAMMA}/events", params={"slug": slug, "closed": "false"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return isinstance(data, list) and len(data) > 0
    except Exception:
        return False


def _step_slug(slug: str, step: int) -> Optional[str]:
    m = re.search(r"(.*-)(\d+)$", slug)
    if not m:
        return None
    base, n = m.group(1), int(m.group(2))
    return f"{base}{n + step}"


def discover_latest_btc_5m_slug(max_pages: int = 12) -> tuple[Optional[str], str]:
    """
    Returns (market_slug, reason).
    Scans public CLOB markets and picks the latest active BTC 5m-style market.
    Fallback: ID stepping heuristic (+step) with existence check.
    """
    try:
        client = ClobClient(HOST, chain_id=CHAIN_ID)
        cursor = "MA=="
        best = None
        best_dt = datetime.min
        scanned = 0

        for _ in range(max_pages):
            payload = client.get_markets(next_cursor=cursor)
            data = payload.get("data", []) if isinstance(payload, dict) else []
            scanned += len(data)

            for m in data:
                if not m.get("active", True):
                    continue
                if m.get("closed", False):
                    continue
                if not _is_btc_5m_market(m):
                    continue

                end_dt = _parse_dt(m.get("end_date_iso"))
                if end_dt >= best_dt:
                    best_dt = end_dt
                    best = m

            cursor = payload.get("next_cursor") if isinstance(payload, dict) else None
            if not cursor:
                break

        if best and best.get("market_slug"):
            slug = str(best.get("market_slug"))
            _save_last_slug(slug)
            return slug, f"clob_discovery_ok scanned={scanned}"

        # Fallback heuristic: increment suffix by configured step
        if os.getenv("ID_STEP_FALLBACK", "false").lower() == "true":
            step = int(os.getenv("ID_STEP_SIZE", "300"))
            last_slug = _load_last_slug()
            if last_slug:
                candidate = _step_slug(last_slug, step)
                if candidate and _slug_exists_active(candidate):
                    _save_last_slug(candidate)
                    return candidate, f"id_step_fallback_ok from={last_slug} to={candidate}"

        return None, f"clob_discovery_none scanned={scanned}"
    except Exception as e:
        return None, f"clob_discovery_error: {e}"
