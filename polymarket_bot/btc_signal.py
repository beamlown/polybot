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
    candles = r.json()
    candles = list(reversed(candles))[-limit:]
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
    gains = []
    losses = []
    for i in range(1, period + 1):
        delta = closes[-i] - closes[-i - 1]
        gains.append(max(0.0, delta))
        losses.append(max(0.0, -delta))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _vwap(candles: list[dict]) -> float:
    pv = 0.0
    vv = 0.0
    for c in candles:
        p = float(c["close"])
        v = max(0.0, float(c["volume"]))
        pv += p * v
        vv += v
    if vv <= 0:
        return float(candles[-1]["close"])
    return pv / vv


def _stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    var = sum((x - m) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(max(var, 0.0))


def get_btc_signal_prob() -> tuple[float | None, str]:
    """
    Returns (prob_up_next_window, reason).
    Enhanced model: momentum + RSI + VWAP with volatility dampening.
    """
    try:
        s1 = _fetch_series("1m", 12)
        s5 = _fetch_series("5m", 8)
        if len(s1) < 6 or len(s5) < 4:
            return None, "btc_signal_error: insufficient candle data"

        c1 = [x["close"] for x in s1]
        c5 = [x["close"] for x in s5]

        mom_1m = _pct_change(c1[-6], c1[-1])
        mom_5m = _pct_change(c5[-4], c5[-1])

        rsi_1m = _rsi(c1, period=5)
        vwap_1m = _vwap(s1[-10:])
        last = c1[-1]
        vwap_dev = (last - vwap_1m) / vwap_1m if vwap_1m > 0 else 0.0

        # Volatility dampener on 1m returns
        rets = []
        for i in range(1, len(c1)):
            rets.append(_pct_change(c1[i - 1], c1[i]))
        vol = _stdev(rets[-8:])
        damp = 1.0 if vol < 0.0015 else 0.7 if vol < 0.003 else 0.45

        # 3-signal agreement score
        score_mom = (mom_1m * 0.60) + (mom_5m * 0.40)
        score_rsi = (rsi_1m - 50.0) / 50.0  # -1..+1
        score_vwap = max(-1.0, min(1.0, vwap_dev * 25.0))

        score = (score_mom * 70.0) + (score_rsi * 0.20) + (score_vwap * 0.10)
        score *= damp

        prob = 0.5 + max(-0.25, min(0.25, score))
        prob = max(0.05, min(0.95, prob))

        # agreement flag (2/3 directional agreement)
        up_votes = 0
        up_votes += 1 if score_mom > 0 else 0
        up_votes += 1 if score_rsi > 0 else 0
        up_votes += 1 if score_vwap > 0 else 0
        agree = "up" if up_votes >= 2 else "down" if up_votes <= 1 else "mixed"

        reason = (
            f"btc_momentum 1m={mom_1m:.4%}, 5m={mom_5m:.4%}, "
            f"rsi1m={rsi_1m:.1f}, vwap_dev={vwap_dev:.3%}, vol={vol:.4%}, agree={agree}, "
            f"model_up_prob={prob*100:.1f}%"
        )
        return prob, reason
    except Exception as e:
        return None, f"btc_signal_error: {e}"
