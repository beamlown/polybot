from typing import Optional, Tuple

import requests

from v4_errors import E_SIGNAL_HTTP, E_SIGNAL_PARSE, fmt


def _pct(a: float, b: float) -> float:
    return 0.0 if a <= 0 else (b - a) / a


def _binance(interval: str, limit: int):
    r = requests.get(
        "https://api.binance.com/api/v3/klines",
        params={"symbol": "BTCUSDT", "interval": interval, "limit": limit},
        timeout=10,
    )
    r.raise_for_status()
    return [float(x[4]) for x in r.json()]


def _coinbase(granularity: int, limit: int):
    r = requests.get(
        "https://api.exchange.coinbase.com/products/BTC-USD/candles",
        params={"granularity": granularity},
        timeout=10,
    )
    r.raise_for_status()
    rows = list(reversed(r.json()))[-limit:]
    return [float(x[4]) for x in rows]


def _series(interval: str, limit: int):
    try:
        return _binance(interval, limit)
    except Exception:
        return _coinbase(60 if interval == "1m" else 300, limit)


def signal_up_prob() -> Tuple[Optional[float], Optional[str], Optional[str]]:
    try:
        c1 = _series("1m", 8)
        c5 = _series("5m", 5)
    except Exception as e:
        return None, None, fmt(E_SIGNAL_HTTP, f"price source failed: {e}")

    try:
        m1 = _pct(c1[-6], c1[-1])
        m5 = _pct(c5[-4], c5[-1])
        score = (m1 * 0.65) + (m5 * 0.35)
        prob = 0.5 + max(-0.25, min(0.25, score * 90))
        prob = max(0.05, min(0.95, prob))
        text = f"short_trend={m1:.3%} | medium_trend={m5:.3%} | up_chance={prob*100:.1f}%"
        return prob, text, None
    except Exception as e:
        return None, None, fmt(E_SIGNAL_PARSE, f"signal parse failed: {e}")
