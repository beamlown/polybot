import requests


def _fetch_binance_klines(interval: str, limit: int):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": "BTCUSDT", "interval": interval, "limit": limit}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def _pct_change(first_close: float, last_close: float) -> float:
    if first_close <= 0:
        return 0.0
    return (last_close - first_close) / first_close


def get_btc_signal_prob() -> tuple[float | None, str]:
    """
    Returns (prob_up_next_window, reason).
    Very simple momentum model for short-window BTC markets.
    """
    try:
        m1 = _fetch_binance_klines("1m", 6)   # ~5 mins momentum
        m5 = _fetch_binance_klines("5m", 4)   # ~15 mins momentum

        c1_first = float(m1[0][4])
        c1_last = float(m1[-1][4])
        c5_first = float(m5[0][4])
        c5_last = float(m5[-1][4])

        mom_1m = _pct_change(c1_first, c1_last)
        mom_5m = _pct_change(c5_first, c5_last)

        # map momentum to probability around 0.5
        score = (mom_1m * 0.65) + (mom_5m * 0.35)
        prob = 0.5 + max(-0.2, min(0.2, score * 80))
        prob = max(0.05, min(0.95, prob))

        reason = f"btc_momentum 1m={mom_1m:.4%}, 5m={mom_5m:.4%}"
        return prob, reason
    except Exception as e:
        return None, f"btc_signal_error: {e}"
