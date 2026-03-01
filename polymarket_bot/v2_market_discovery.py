import json
import os
from dataclasses import dataclass
from typing import Optional

import requests

GAMMA = "https://gamma-api.polymarket.com"


@dataclass
class RoundMarket:
    slug: str
    question: str
    market_id: str
    yes_price: float
    yes_token_id: Optional[str]
    no_token_id: Optional[str]


def _parse_token_ids(raw) -> tuple[Optional[str], Optional[str]]:
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


def discover_current_round(series_prefix: str = "btc-updown", round_minutes: int = 5) -> Optional[RoundMarket]:
    token = f"{series_prefix}-{round_minutes}m"
    resp = requests.get(
        f"{GAMMA}/markets",
        params={
            "limit": 500,
            "active": "true",
            "closed": "false",
            "order": "startDate",
            "ascending": "false",
        },
        timeout=15,
    )
    resp.raise_for_status()
    markets = resp.json()
    if not isinstance(markets, list):
        return None

    candidates = []
    for m in markets:
        slug = str(m.get("slug") or "")
        question = str(m.get("question") or "")
        blob = f"{slug.lower()} {question.lower()}"
        if token not in blob:
            continue

        op = m.get("outcomePrices")
        if isinstance(op, str):
            try:
                op = json.loads(op)
            except Exception:
                op = []
        if not isinstance(op, list) or len(op) < 1:
            continue

        try:
            yes_price = float(op[0])
        except Exception:
            continue
        if not (0 < yes_price < 1):
            continue

        yes_token, no_token = _parse_token_ids(m.get("clobTokenIds"))
        market_id = str(m.get("id") or m.get("conditionId") or slug)
        candidates.append(RoundMarket(slug, question, market_id, yes_price, yes_token, no_token))

    if not candidates:
        return None

    # Newest by slug suffix if possible
    def suffix_val(s: str) -> int:
        try:
            return int(s.rsplit("-", 1)[-1])
        except Exception:
            return 0

    candidates.sort(key=lambda c: suffix_val(c.slug), reverse=True)
    return candidates[0]
