import json
import time
from dataclasses import dataclass
from datetime import datetime, UTC
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
    best_bid: Optional[float]
    best_ask: Optional[float]
    gamma_spread: Optional[float]
    start_ts: Optional[int]
    end_ts: Optional[int]
    volume24h: Optional[float]


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


def _parse_iso_ts(value) -> Optional[int]:
    try:
        if value is None:
            return None
        s = str(value).strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return int(dt.timestamp())
    except Exception:
        return None


def _is_unixish_suffix(v: int) -> bool:
    return 1_600_000_000 < v < 2_200_000_000


def discover(series_prefix: str, round_minutes: int, force_slug: Optional[str] = None) -> tuple[Optional[MarketRound], Optional[str]]:
    token = f"{series_prefix}-{round_minutes}m"
    force = (force_slug or "").strip().lower()

    try:
        # If user pins a slug, query that exact slug directly first.
        if force:
            r = requests.get(
                f"{GAMMA_API}/markets",
                params={"slug": force, "limit": 10, "active": "true", "closed": "false"},
                timeout=20,
            )
            r.raise_for_status()
            data = r.json()
        else:
            # Deterministic current-round probing first: now bucket +/- nearby buckets.
            interval = max(60, round_minutes * 60)
            now = int(time.time())
            cur_bucket = (now // interval) * interval
            probe_offsets = [0, -1, 1, -2, 2, -3, 3, -4, 4]
            probe_hits = []
            for off in probe_offsets:
                slug_probe = f"{token}-{cur_bucket + off * interval}"
                rr = requests.get(
                    f"{GAMMA_API}/markets",
                    params={"slug": slug_probe, "limit": 3, "active": "true", "closed": "false"},
                    timeout=10,
                )
                rr.raise_for_status()
                payload = rr.json()
                if isinstance(payload, list) and payload:
                    probe_hits.extend(payload)
            if probe_hits:
                data = probe_hits
            else:
                # Fallback broad scan
                r = requests.get(
                    f"{GAMMA_API}/markets",
                    params={
                        "limit": 2000,
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
    total_markets = len(data)
    token_candidates = 0
    seen_slugs: list[str] = []
    token_seen_slugs: list[str] = []

    for m in data:
        try:
            slug = str(m.get("slug") or "")
            slug_l = slug.lower()
            q = str(m.get("question") or "")
            blob = f"{slug_l} {q.lower()}"
            seen_slugs.append(slug)

            pattern_ok = slug_l.startswith(token) or (token in slug_l)
            if pattern_ok:
                token_seen_slugs.append(slug)

            if force:
                if slug_l != force:
                    continue
            elif not pattern_ok:
                continue

            token_candidates += 1

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

            # Suffix sanity: if suffix looks timestamp-like, require reasonable recency window.
            if _is_unixish_suffix(sfx):
                now_ts = int(time.time())
                if abs(now_ts - sfx) > 24 * 60 * 60:
                    continue

            # Parse optional timestamps for diagnostics only.
            start_ts = _parse_iso_ts(m.get("startDateIso") or m.get("startDate"))
            end_ts = _parse_iso_ts(m.get("endDateIso") or m.get("endDate"))

            best_bid = None
            best_ask = None
            gamma_spread = None
            try:
                if m.get("bestBid") is not None:
                    best_bid = float(m.get("bestBid"))
            except Exception:
                pass
            try:
                if m.get("bestAsk") is not None:
                    best_ask = float(m.get("bestAsk"))
            except Exception:
                pass
            try:
                if m.get("spread") is not None:
                    gamma_spread = float(m.get("spread"))
            except Exception:
                pass

            volume24h = None
            try:
                if m.get("volume24hr") is not None:
                    volume24h = float(m.get("volume24hr"))
            except Exception:
                pass

            out.append(MarketRound(slug, market_id, q, yes, 1 - yes, yes_id, no_id, sfx, best_bid, best_ask, gamma_spread, start_ts, end_ts, volume24h))
        except Exception:
            continue

    if not out:
        nearby = []
        now = int(time.time())
        interval = max(60, round_minutes * 60)
        cur_bucket = (now // interval) * interval

        source_slugs = token_seen_slugs if token_seen_slugs else seen_slugs
        for s in source_slugs:
            sfx = _suffix(s)
            if sfx > 0:
                nearby.append((abs(sfx - cur_bucket), s))

        nearby.sort(key=lambda x: x[0])
        closest = [x[1] for x in nearby[:5]]
        force_found = (force in [s.lower() for s in seen_slugs]) if force else False

        detail = (
            f"no matching active round found | total_markets={total_markets} "
            f"| token_candidates={token_candidates} | force_slug={force or 'none'} "
            f"| force_found={force_found} | closest_slugs={closest}"
        )
        return None, fmt(E_DISCOVERY_NONE, detail)

    if force:
        out.sort(key=lambda x: x.suffix, reverse=True)
        return out[0], None

    # Prefer rounds near current time bucket and reject day-away buckets.
    now = int(time.time())
    interval = max(60, round_minutes * 60)
    cur_bucket = (now // interval) * interval
    max_distance = interval * 6  # keep within ~30 minutes for 5m rounds

    near = [m for m in out if abs(m.suffix - cur_bucket) <= max_distance]
    target = near if near else []

    if not target:
        nearby = sorted([(abs(m.suffix - cur_bucket), m.slug) for m in out], key=lambda x: x[0])[:5]
        closest = [x[1] for x in nearby]
        detail = (
            f"no matching active round found | total_markets={total_markets} "
            f"| token_candidates={token_candidates} | force_slug=none | force_found=False "
            f"| closest_slugs={closest}"
        )
        return None, fmt(E_DISCOVERY_NONE, detail)

    target.sort(key=lambda x: (abs(x.suffix - cur_bucket), -x.suffix))
    return target[0], None
