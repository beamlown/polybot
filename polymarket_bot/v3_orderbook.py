from dataclasses import dataclass
from typing import Optional

from py_clob_client.client import ClobClient


@dataclass
class BookStats:
    midpoint: Optional[float]
    spread: Optional[float]
    best_buy: Optional[float]
    best_sell: Optional[float]
    bid_depth_top5: float
    ask_depth_top5: float
    imbalance: float


class OrderBookReader:
    def __init__(self, host: str = "https://clob.polymarket.com", chain_id: int = 137):
        self.client = ClobClient(host, chain_id=chain_id)

    def stats(self, token_id: str) -> BookStats:
        book = self.client.get_order_book(token_id)

        bids = sorted(book.bids, key=lambda x: float(x.price), reverse=True)
        asks = sorted(book.asks, key=lambda x: float(x.price))

        bid_depth = sum(float(x.size) for x in bids[:5]) if bids else 0.0
        ask_depth = sum(float(x.size) for x in asks[:5]) if asks else 0.0
        total = bid_depth + ask_depth
        imbalance = ((bid_depth - ask_depth) / total) if total > 0 else 0.0

        midpoint = None
        spread = None
        best_buy = None
        best_sell = None

        try:
            midpoint = float(self.client.get_midpoint(token_id)["mid"])
        except Exception:
            pass
        try:
            best_buy = float(self.client.get_price(token_id, side="BUY")["price"])
        except Exception:
            pass
        try:
            best_sell = float(self.client.get_price(token_id, side="SELL")["price"])
        except Exception:
            pass
        try:
            spread = float(self.client.get_spread(token_id)["spread"])
        except Exception:
            pass

        return BookStats(
            midpoint=midpoint,
            spread=spread,
            best_buy=best_buy,
            best_sell=best_sell,
            bid_depth_top5=bid_depth,
            ask_depth_top5=ask_depth,
            imbalance=imbalance,
        )
