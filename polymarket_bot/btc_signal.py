import requests


def _pct_change(first_close: float, last_close: float) -> float:
    if first_close <= 0:
        return 0.0
    return (last_close - first_close) / first_close


def _fetch_binance_klines(interval: str, limit: int):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": "BTCUSDT", "interval": interval, "limit": limit}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return [float(x[4]) for x in r.json()]  # close prices


def _fetch_coinbase_candles(granularity: int, limit: int):
    # Coinbase candles: [time, low, high, open, close, volume]
    url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
    params = {"granularity": granularity}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    candles = r.json()
    # response is newest-first; reverse to oldest-first and trim
    candles = list(reversed(candles))[-limit:]
    return [float(c[4]) for c in candles]


def _fetch_close_series(interval_label: str, limit: int) -> list[float]:
    # Try Binance first, fallback to Coinbase when blocked (e.g. 451)
    if interval_label == "1m":
        try:
            return _fetch_binance_klines("1m", limit)
        except Exception:
            return _fetch_coinbase_candles(60, limit)
    if interval_label == "5m":
        try:
            return _fetch_binance_klines("5m", limit)
        except Exception:
            return _fetch_coinbase_candles(300, limit)
    raise ValueError("Unsupported interval")


def get_btc_signal_prob() -> tuple[float | None, str]:
    """
    Returns (prob_up_next_window, reason).
    Simple momentum model for short-window BTC markets.
    """
    try:
        m1 = _fetch_close_series("1m", 6)   # ~5 mins momentum
        m5 = _fetch_close_series("5m", 4)   # ~15 mins momentum

        if len(m1) < 2 or len(m5) < 2:
            return None, "btc_signal_error: insufficient candle data"

        mom_1m = _pct_change(m1[0], m1[-1])
        mom_5m = _pct_change(m5[0], m5[-1])

        score = (mom_1m * 0.65) + (mom_5m * 0.35)
        prob = 0.5 + max(-0.2, min(0.2, score * 80))
        prob = max(0.05, min(0.95, prob))

        reason = f"btc_momentum 1m={mom_1m:.4%}, 5m={mom_5m:.4%}, model_up_prob={prob*100:.1f}%"
        return prob, reason
    except Exception as e:
        return None, f"btc_signal_error: {e}"
