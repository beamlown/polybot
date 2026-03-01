import json
import time
from dataclasses import dataclass
from typing import Optional

import requests

from v4_errors import E_DISCOVERY_HTTP, E_DISCOVERY_PARSE, E_DISCOVERY_NONE, fmt

GAMMA_API = "https://gamma-api.polymarket.com"


@dataclass
class MarketRound:
    slug: str
    market_id: str
    question: str
    yes_price: float
    no_price: float
    yes_token_id: Optional[str]
    no_token_id: Optional[str]
    suffix: int


def _suffix(slug: str) -> int:
    try:
        return int(str(slug).rsplit("-", 1)[-1])
    except Exception:
        return 0


def _token_ids(raw) -> tuple[Optional[str], Optional[str]]:
    if raw is None:
        return None, None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return None, None
    if isinstance(raw, list) and len(raw) >= 2:
        return str(raw[0]), str(raw[1])
    return None, None


def discover(series_prefix: str, round_minutes: int, force_slug: Optional[str] = None) -> tuple[Optional[MarketRound], Optional[str]]:
    token = f"{series_prefix}-{round_minutes}m"

    try:
        r = requests.get(
            f"{GAMMA_API}/markets",
            params={
                "limit": 600,
                "active": "true",
                "closed": "false",
                "order": "startDate",
                "ascending": "false",
            },
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return None, fmt(E_DISCOVERY_HTTP, f"gamma /markets request failed: {e}")

    if not isinstance(data, list):
        return None, fmt(E_DISCOVERY_PARSE, "gamma /markets returned non-list payload")

    out = []
    force = (force_slug or "").strip().lower()

    for m in data:
        try:
            slug = str(m.get("slug") or "")
            slug_l = slug.lower()
            q = str(m.get("question") or "")
            blob = f"{slug_l} {q.lower()}"

            if force:
                if slug_l != force:
                    continue
            elif token not in blob:
                continue

            op = m.get("outcomePrices")
            if isinstance(op, str):
                op = json.loads(op)
            if not isinstance(op, list) or not op:
                continue

            yes = float(op[0])
            if not (0 < yes < 1):
                continue

            yes_id, no_id = _token_ids(m.get("clobTokenIds"))
            market_id = str(m.get("id") or m.get("conditionId") or slug)
            sfx = _suffix(slug)
            if sfx <= 0:
                continue

            # hard freshness gate around current clock
            now = int(time.time())
            interval = max(60, round_minutes * 60)
            cur_bucket = (now // interval) * interval
            if not force:
                if abs(sfx - cur_bucket) > (interval * 2):
                    continue

            out.append(MarketRound(slug, market_id, q, yes, 1 - yes, yes_id, no_id, sfx))
        except Exception:
            continue

    if not out:
        return None, fmt(E_DISCOVERY_NONE, "no matching active round found")

    out.sort(key=lambda x: x.suffix, reverse=True)
    return out[0], None
