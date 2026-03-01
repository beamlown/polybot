import requests


def _pct(a: float, b: float) -> float:
    return 0.0 if a <= 0 else (b - a) / a


def _fetch_binance(interval: str, limit: int):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": "BTCUSDT", "interval": interval, "limit": limit}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return [float(x[4]) for x in r.json()]


def _fetch_coinbase(granularity: int, limit: int):
    url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
    r = requests.get(url, params={"granularity": granularity}, timeout=10)
    r.raise_for_status()
    candles = list(reversed(r.json()))[-limit:]
    return [float(c[4]) for c in candles]


def _fetch(interval: str, limit: int):
    try:
        return _fetch_binance(interval, limit)
    except Exception:
        return _fetch_coinbase(60 if interval == "1m" else 300, limit)


def get_up_probability() -> tuple[float | None, str]:
    try:
        c1 = _fetch("1m", 8)
        c5 = _fetch("5m", 5)
        m1 = _pct(c1[-6], c1[-1])
        m5 = _pct(c5[-4], c5[-1])
        score = (m1 * 0.65) + (m5 * 0.35)
        prob = 0.5 + max(-0.25, min(0.25, score * 90))
        prob = max(0.05, min(0.95, prob))
        reason = f"short_trend={m1:.3%} | medium_trend={m5:.3%} | up_chance={prob*100:.1f}%"
        return prob, reason
    except Exception as e:
        return None, f"signal_error: {e}"
