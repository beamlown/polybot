from datetime import datetime
from typing import Optional

from py_clob_client.client import ClobClient


HOST = "https://clob.polymarket.com"
CHAIN_ID = 137


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


def discover_latest_btc_5m_slug(max_pages: int = 12) -> tuple[Optional[str], str]:
    """
    Returns (market_slug, reason).
    Scans public CLOB markets and picks the latest active BTC 5m-style market.
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
            return str(best.get("market_slug")), f"clob_discovery_ok scanned={scanned}"

        return None, f"clob_discovery_none scanned={scanned}"
    except Exception as e:
        return None, f"clob_discovery_error: {e}"
