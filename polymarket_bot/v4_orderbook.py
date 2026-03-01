from dataclasses import dataclass
from typing import Optional, Tuple

from py_clob_client.client import ClobClient

from v4_errors import E_ORDERBOOK_HTTP, E_ORDERBOOK_PARSE, E_ORDERBOOK_EMPTY, fmt


@dataclass
class OBStats:
    spread: Optional[float]
    midpoint: Optional[float]
    depth_top5: float
    imbalance: float


class OBReader:
    def __init__(self, host: str = "https://clob.polymarket.com", chain_id: int = 137):
        self.c = ClobClient(host, chain_id=chain_id)

    def read(self, token_id: Optional[str]) -> Tuple[Optional[OBStats], Optional[str]]:
        if not token_id:
            return None, fmt(E_ORDERBOOK_EMPTY, "missing token id")
        try:
            book = self.c.get_order_book(token_id)
        except Exception as e:
            return None, fmt(E_ORDERBOOK_HTTP, f"orderbook request failed: {e}")

        try:
            bids = sorted(book.bids, key=lambda x: float(x.price), reverse=True)
            asks = sorted(book.asks, key=lambda x: float(x.price))
            bid_depth = sum(float(x.size) for x in bids[:5]) if bids else 0.0
            ask_depth = sum(float(x.size) for x in asks[:5]) if asks else 0.0
            total = bid_depth + ask_depth
            imbalance = ((bid_depth - ask_depth) / total) if total > 0 else 0.0
            depth = total

            spread = None
            midpoint = None
            try:
                spread = float(self.c.get_spread(token_id)["spread"])
            except Exception:
                pass
            try:
                midpoint = float(self.c.get_midpoint(token_id)["mid"])
            except Exception:
                pass

            return OBStats(spread, midpoint, depth, imbalance), None
        except Exception as e:
            return None, fmt(E_ORDERBOOK_PARSE, f"orderbook parse failed: {e}")
