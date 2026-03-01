import json
import time
from dataclasses import dataclass
from typing import Optional

import requests

GAMMA_API = "https://gamma-api.polymarket.com"


@dataclass
class V3Market:
    slug: str
    market_id: str
    question: str
    yes_price: float
    no_price: float
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


def _slug_suffix(slug: str) -> int:
    try:
        return int(str(slug).rsplit("-", 1)[-1])
    except Exception:
        return 0


def discover_latest_market(series_prefix: str = "btc-updown", round_minutes: int = 5) -> Optional[V3Market]:
    token = f"{series_prefix}-{round_minutes}m"
    resp = requests.get(
        f"{GAMMA_API}/markets",
        params={
            "limit": 500,
            "active": "true",
            "closed": "false",
            "order": "startDate",
            "ascending": "false",
        },
        timeout=20,
    )
    resp.raise_for_status()
    markets = resp.json()
    if not isinstance(markets, list):
        return None

    out = []
    for m in markets:
        slug = str(m.get("slug") or "")
        question = str(m.get("question") or "")
        blob = f"{slug.lower()} {question.lower()}"
        if token not in blob:
            continue

        outcome_prices = m.get("outcomePrices")
        if isinstance(outcome_prices, str):
            try:
                outcome_prices = json.loads(outcome_prices)
            except Exception:
                outcome_prices = []

        if not isinstance(outcome_prices, list) or len(outcome_prices) < 1:
            continue

        try:
            yes_price = float(outcome_prices[0])
        except Exception:
            continue

        if yes_price <= 0 or yes_price >= 1:
            continue

        yes_token_id, no_token_id = _parse_token_ids(m.get("clobTokenIds"))
        market_id = str(m.get("id") or m.get("conditionId") or slug)

        out.append(
            V3Market(
                slug=slug,
                market_id=market_id,
                question=question,
                yes_price=yes_price,
                no_price=(1.0 - yes_price),
                yes_token_id=yes_token_id,
                no_token_id=no_token_id,
            )
        )

    if not out:
        return None

    # Freshness guard: keep rounds near current wall-clock bucket.
    now_ts = int(time.time())
    interval = max(60, round_minutes * 60)
    current_bucket = (now_ts // interval) * interval
    max_drift = interval * 2  # within +/- 2 rounds

    near = [m for m in out if abs(_slug_suffix(m.slug) - current_bucket) <= max_drift]
    target = near if near else out

    target.sort(key=lambda x: _slug_suffix(x.slug), reverse=True)
    return target[0]
