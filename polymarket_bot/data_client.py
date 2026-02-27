from dataclasses import dataclass
from typing import List


@dataclass
class Market:
    market_id: str
    question: str
    yes_price: float  # 0..1
    signal_prob: float  # your model estimate placeholder


class MarketClient:
    """
    Stub client. Replace fetch_markets() with real Polymarket reads.
    """

    def fetch_markets(self) -> List[Market]:
        # Demo data so bot runs immediately
        return [
            Market("demo-1", "Will X happen by date?", 0.42, 0.50),
            Market("demo-2", "Will Y win?", 0.67, 0.61),
            Market("demo-3", "Will Z exceed N?", 0.31, 0.40),
        ]
