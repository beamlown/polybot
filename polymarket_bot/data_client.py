from dataclasses import dataclass
from typing import List
import json
import os
from datetime import datetime, timezone

import requests

try:
    from py_clob_client.client import ClobClient
except Exception:
    ClobClient = None


BASE_URL = "https://gamma-api.polymarket.com"


@dataclass
class Market:
    market_id: str
    question: str
    yes_price: float  # 0..1 (outcome index 0)
    signal_prob: float  # simple placeholder estimate
    end_date: str | None = None
    slug: str | None = None
    outcomes: list[str] | None = None


class MarketClient:
    """Read public market data from Polymarket Gamma API."""

    def __init__(self):
        self.timeout = int(os.getenv("HTTP_TIMEOUT_SECONDS", "20"))
        self.limit = int(os.getenv("EVENT_LIMIT", "100"))
        self.max_days_to_resolution = float(os.getenv("MAX_DAYS_TO_RESOLUTION", "7"))
        self.max_hours_to_resolution = float(os.getenv("MAX_HOURS_TO_RESOLUTION", "0"))
        self.require_started = os.getenv("REQUIRE_STARTED", "true").lower() == "true"
        self.require_end_date = os.getenv("REQUIRE_END_DATE", "true").lower() == "true"
        self.force_event_slug = os.getenv("FORCE_EVENT_SLUG", "").strip()
        self.auto_btc_5m = os.getenv("AUTO_BTC_5M", "true").lower() == "true"
        self.use_clob_markets = os.getenv("USE_CLOB_MARKETS", "true").lower() == "true"
        self.clob_pages = int(os.getenv("CLOB_MARKET_PAGES", "6"))

    def _fetch_events(self) -> list[dict]:
        if self.force_event_slug:
            params = {
                "slug": self.force_event_slug,
                "closed": "false",
            }
            resp = requests.get(f"{BASE_URL}/events", params=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                return data

        params = {
            "closed": "false",
            "limit": self.limit,
        }
        resp = requests.get(f"{BASE_URL}/events", params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        events = data if isinstance(data, list) else []

        if self.auto_btc_5m:
            filtered = []
            for e in events:
                slug = str(e.get("slug") or "").lower()
                title = str(e.get("title") or "").lower()
                text = f"{slug} {title}"
                if "btc-updown-5m" in text or ("bitcoin" in text and "up or down" in text and "5" in text):
                    filtered.append(e)
            if filtered:
                return filtered

        return events

    @staticmethod
    def _parse_outcome_prices(raw_prices) -> list[float]:
        if raw_prices is None:
            return []
        if isinstance(raw_prices, str):
            try:
                raw_prices = json.loads(raw_prices)
            except Exception:
                return []
        if not isinstance(raw_prices, list):
            return []

        out = []
        for p in raw_prices:
            try:
                out.append(float(p))
            except Exception:
                continue
        return out

    @staticmethod
    def _simple_signal_prob(yes_price: float) -> float:
        # Placeholder edge model for paper testing only.
        # Replace with your own model later.
        return min(0.99, max(0.01, yes_price + 0.06))

    def _fetch_markets_clob(self) -> List[Market]:
        if ClobClient is None:
            return []

        markets: List[Market] = []
        now = datetime.now(timezone.utc)

        try:
            client = ClobClient("https://clob.polymarket.com", chain_id=137)
            cursor = "MA=="

            for _ in range(self.clob_pages):
                payload = client.get_markets(next_cursor=cursor)
                data = payload.get("data", []) if isinstance(payload, dict) else []

                for m in data:
                    if not m.get("active", True):
                        continue
                    if m.get("closed", False):
                        continue

                    slug = str(m.get("market_slug") or "")
                    question = str(m.get("question") or "Unknown market")

                    if self.force_event_slug and self.force_event_slug.lower() not in slug.lower():
                        continue

                    if self.auto_btc_5m:
                        text = f"{slug.lower()} {question.lower()}"
                        if "btc-updown-5m" not in text and not ("bitcoin" in text and "up or down" in text and "5" in text):
                            continue

                    end_date_raw = m.get("end_date_iso")
                    if end_date_raw:
                        try:
                            end_dt = datetime.fromisoformat(str(end_date_raw).replace("Z", "+00:00"))
                            days_left = (end_dt - now).total_seconds() / 86400
                            if days_left < 0:
                                continue
                        except Exception:
                            pass

                    tokens = m.get("tokens") or []
                    if not isinstance(tokens, list) or len(tokens) < 2:
                        continue

                    try:
                        yes_price = float(tokens[0].get("price"))
                    except Exception:
                        continue

                    if yes_price <= 0 or yes_price >= 1:
                        continue

                    outcomes = []
                    for t in tokens[:2]:
                        outcomes.append(str(t.get("outcome") or ""))

                    market_id = str(m.get("condition_id") or m.get("question_id") or slug or "unknown")
                    markets.append(
                        Market(
                            market_id=market_id,
                            question=question,
                            yes_price=yes_price,
                            signal_prob=self._simple_signal_prob(yes_price),
                            end_date=end_date_raw,
                            slug=slug,
                            outcomes=outcomes,
                        )
                    )

                cursor = payload.get("next_cursor") if isinstance(payload, dict) else None
                if not cursor:
                    break
        except Exception:
            return []

        return markets

    def fetch_markets(self) -> List[Market]:
        if self.use_clob_markets:
            clob_markets = self._fetch_markets_clob()
            if clob_markets:
                return clob_markets

        events = self._fetch_events()
        markets: List[Market] = []

        now = datetime.now(timezone.utc)

        for event in events:
            event_markets = event.get("markets", []) or []
            for m in event_markets:
                if not m.get("active", True):
                    continue

                apply_time_filters = not bool(self.force_event_slug)

                start_date_raw = m.get("startDate") or event.get("startDate")
                if apply_time_filters and self.require_started and start_date_raw:
                    try:
                        start_dt = datetime.fromisoformat(str(start_date_raw).replace("Z", "+00:00"))
                        if start_dt > now:
                            continue
                    except Exception:
                        pass

                end_date_raw = (
                    m.get("endDate")
                    or m.get("endDateIso")
                    or event.get("endDate")
                    or event.get("endDateIso")
                    or m.get("closedTime")
                )
                if apply_time_filters and (not end_date_raw and self.require_end_date):
                    continue

                if apply_time_filters and end_date_raw:
                    try:
                        end_dt = datetime.fromisoformat(str(end_date_raw).replace("Z", "+00:00"))
                        days_left = (end_dt - now).total_seconds() / 86400
                        if days_left < 0:
                            continue
                        max_days = self.max_days_to_resolution
                        if self.max_hours_to_resolution > 0:
                            max_days = self.max_hours_to_resolution / 24.0
                        if days_left > max_days:
                            continue
                    except Exception:
                        if self.require_end_date:
                            continue

                prices = self._parse_outcome_prices(m.get("outcomePrices"))
                if not prices:
                    continue

                yes_price = prices[0]
                market_q = m.get("question") or m.get("title") or ""
                event_title = event.get("title") or ""
                if market_q and event_title:
                    question = f"{event_title} | {market_q}"
                else:
                    question = market_q or event_title or "Unknown market"
                market_id = str(m.get("id") or m.get("conditionId") or m.get("slug") or "unknown")

                if yes_price <= 0 or yes_price >= 1:
                    continue

                markets.append(
                    Market(
                        market_id=market_id,
                        question=question,
                        yes_price=yes_price,
                        signal_prob=self._simple_signal_prob(yes_price),
                        end_date=end_date_raw,
                        slug=m.get("slug") or event.get("slug"),
                        outcomes=(m.get("outcomes") if isinstance(m.get("outcomes"), list) else None),
                    )
                )

        return markets
