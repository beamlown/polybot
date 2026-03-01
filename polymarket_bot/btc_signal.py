import math
import requests


def _pct_change(first_close: float, last_close: float) -> float:
    if first_close <= 0:
        return 0.0
    return (last_close - first_close) / first_close


def _fetch_binance_candles(interval: str, limit: int):
    # [open_time, open, high, low, close, volume, ...]
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": "BTCUSDT", "interval": interval, "limit": limit}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    raw = r.json()
    return [{"close": float(x[4]), "volume": float(x[5])} for x in raw]


def _fetch_coinbase_candles(granularity: int, limit: int):
    # [time, low, high, open, close, volume]
    url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
    params = {"granularity": granularity}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    candles = list(reversed(r.json()))[-limit:]
    return [{"close": float(c[4]), "volume": float(c[5])} for c in candles]


def _fetch_series(interval_label: str, limit: int):
    if interval_label == "1m":
        try:
            return _fetch_binance_candles("1m", limit)
        except Exception:
            return _fetch_coinbase_candles(60, limit)
    if interval_label == "5m":
        try:
            return _fetch_binance_candles("5m", limit)
        except Exception:
            return _fetch_coinbase_candles(300, limit)
    raise ValueError("Unsupported interval")


def _rsi(closes: list[float], period: int = 5) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, period + 1):
        d = closes[-i] - closes[-i - 1]
        gains.append(max(0.0, d))
        losses.append(max(0.0, -d))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _vwap(candles: list[dict]) -> float:
    pv, vv = 0.0, 0.0
    for c in candles:
        p = float(c["close"])
        v = max(0.0, float(c["volume"]))
        pv += p * v
        vv += v
    return (pv / vv) if vv > 0 else float(candles[-1]["close"])


def _stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / (len(values) - 1))


def get_btc_signal_prob() -> tuple[float | None, str]:
    """
    Returns (prob_up_next_window, reason).
    Human-readable signal labels to keep console clean.
    """
    try:
        s1 = _fetch_series("1m", 12)
        s5 = _fetch_series("5m", 8)
        if len(s1) < 6 or len(s5) < 4:
            return None, "signal_error: not enough data"

        c1 = [x["close"] for x in s1]
        c5 = [x["close"] for x in s5]

        short_trend = _pct_change(c1[-6], c1[-1])
        medium_trend = _pct_change(c5[-4], c5[-1])

        market_heat = _rsi(c1, period=5)
        avg_price = _vwap(s1[-10:])
        last = c1[-1]
        price_vs_avg = (last - avg_price) / avg_price if avg_price > 0 else 0.0

        rets = [_pct_change(c1[i - 1], c1[i]) for i in range(1, len(c1))]
        choppiness = _stdev(rets[-8:])
        damp = 1.0 if choppiness < 0.0015 else 0.7 if choppiness < 0.003 else 0.45

        score_trend = (short_trend * 0.60) + (medium_trend * 0.40)
        score_heat = (market_heat - 50.0) / 50.0
        score_avg = max(-1.0, min(1.0, price_vs_avg * 25.0))

        score = ((score_trend * 70.0) + (score_heat * 0.20) + (score_avg * 0.10)) * damp
        prob = 0.5 + max(-0.25, min(0.25, score))
        prob = max(0.05, min(0.95, prob))

        up_votes = (1 if score_trend > 0 else 0) + (1 if score_heat > 0 else 0) + (1 if score_avg > 0 else 0)
        direction_vote = "up" if up_votes >= 2 else "down"

        reason = (
            f"short_trend={short_trend:.3%} | medium_trend={medium_trend:.3%} | "
            f"market_heat={market_heat:.0f}/100 | price_vs_avg={price_vs_avg:.2%} | "
            f"choppiness={choppiness:.2%} | vote={direction_vote} | up_chance={prob*100:.1f}%"
        )
        return prob, reason
    except Exception as e:
        return None, f"signal_error: {e}"
