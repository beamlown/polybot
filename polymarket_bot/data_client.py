from dataclasses import dataclass
from typing import List
import json
import os

import requests


BASE_URL = "https://gamma-api.polymarket.com"


@dataclass
class Market:
    market_id: str
    question: str
    yes_price: float  # 0..1
    signal_prob: float  # simple placeholder estimate


class MarketClient:
    """Read public market data from Polymarket Gamma API."""

    def __init__(self):
        self.timeout = int(os.getenv("HTTP_TIMEOUT_SECONDS", "20"))
        self.limit = int(os.getenv("EVENT_LIMIT", "100"))

    def _fetch_events(self) -> list[dict]:
        params = {
            "closed": "false",
            "limit": self.limit,
        }
        resp = requests.get(f"{BASE_URL}/events", params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []

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

    def fetch_markets(self) -> List[Market]:
        events = self._fetch_events()
        markets: List[Market] = []

        for event in events:
            event_markets = event.get("markets", []) or []
            for m in event_markets:
                if not m.get("active", True):
                    continue

                prices = self._parse_outcome_prices(m.get("outcomePrices"))
                if not prices:
                    continue

                yes_price = prices[0]
                question = m.get("question") or m.get("title") or event.get("title") or "Unknown market"
                market_id = str(m.get("id") or m.get("conditionId") or m.get("slug") or "unknown")

                if yes_price <= 0 or yes_price >= 1:
                    continue

                markets.append(
                    Market(
                        market_id=market_id,
                        question=question,
                        yes_price=yes_price,
                        signal_prob=self._simple_signal_prob(yes_price),
                    )
                )

        return markets
