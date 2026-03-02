from typing import Optional, Tuple

import requests

from v4_errors import E_SIGNAL_HTTP, E_SIGNAL_PARSE, fmt


def _pct(a: float, b: float) -> float:
    return 0.0 if a <= 0 else (b - a) / a


def _binance(interval: str, limit: int, symbol: str):
    r = requests.get(
        "https://api.binance.com/api/v3/klines",
        params={"symbol": symbol, "interval": interval, "limit": limit},
        timeout=10,
    )
    r.raise_for_status()
    return [float(x[4]) for x in r.json()]


def _coinbase(granularity: int, limit: int, product: str):
    r = requests.get(
        f"https://api.exchange.coinbase.com/products/{product}/candles",
        params={"granularity": granularity},
        timeout=10,
    )
    r.raise_for_status()
    rows = list(reversed(r.json()))[-limit:]
    return [float(x[4]) for x in rows]


def _series(interval: str, limit: int, symbol: str, product: str):
    try:
        return _binance(interval, limit, symbol)
    except Exception:
        return _coinbase(60 if interval == "1m" else 300, limit, product)


def _ema(values: list[float], span: int) -> float:
    if not values:
        return 0.0
    alpha = 2.0 / (span + 1.0)
    out = values[0]
    for v in values[1:]:
        out = (alpha * v) + ((1.0 - alpha) * out)
    return out


def _rsi(values: list[float], period: int = 14) -> float:
    if len(values) < period + 1:
        return 50.0
    gains = 0.0
    losses = 0.0
    for i in range(-period, 0):
        d = values[i] - values[i - 1]
        if d >= 0:
            gains += d
        else:
            losses += -d
    if losses == 0:
        return 100.0
    rs = (gains / period) / (losses / period)
    return 100.0 - (100.0 / (1.0 + rs))


def signal_up_prob(asset: str = "BTC") -> Tuple[Optional[float], Optional[str], Optional[str]]:
    asset_u = str(asset or "BTC").upper()
    if asset_u.startswith("SOL"):
        symbol, product = "SOLUSDT", "SOL-USD"
    elif asset_u.startswith("ETH"):
        symbol, product = "ETHUSDT", "ETH-USD"
    elif asset_u.startswith("XRP"):
        symbol, product = "XRPUSDT", "XRP-USD"
    else:
        symbol, product = "BTCUSDT", "BTC-USD"
    try:
        c1 = _series("1m", 60, symbol, product)
        c5 = _series("5m", 100, symbol, product)
    except Exception as e:
        return None, None, fmt(E_SIGNAL_HTTP, f"price source failed: {e}")

    try:
        # Momentum
        m1_fast = _pct(c1[-4], c1[-1])
        m1_slow = _pct(c1[-16], c1[-1])
        m5 = _pct(c5[-4], c5[-1])

        # Last-25 candle structure (1m): breadth + body pressure
        last25 = c1[-25:]
        up_candles = 0
        down_candles = 0
        body_sum = 0.0
        for i in range(1, len(last25)):
            d = last25[i] - last25[i - 1]
            body_sum += d
            if d >= 0:
                up_candles += 1
            else:
                down_candles += 1
        candle_breadth = (up_candles - down_candles) / max(1, (up_candles + down_candles))
        candle_body_bias = body_sum / max(1e-9, last25[0])

        # Trend state via EMA spread on 1m
        ema9 = _ema(c1[-20:], 9)
        ema21 = _ema(c1[-30:], 21)
        ema_spread = (ema9 - ema21) / ema21 if ema21 > 0 else 0.0

        # Overbought/oversold pressure
        rsi14 = _rsi(c1, 14)
        rsi_bias = (rsi14 - 50.0) / 50.0  # -1..+1 approx

        # Composite score
        score = (
            (m1_fast * 0.30)
            + (m1_slow * 0.15)
            + (m5 * 0.15)
            + (ema_spread * 0.15)
            + (rsi_bias * 0.05)
            + (candle_breadth * 0.12)
            + (candle_body_bias * 0.08)
        )

        prob = 0.5 + max(-0.30, min(0.30, score * 65.0))
        prob = max(0.03, min(0.97, prob))

        # Human-readable vote card
        bull_votes = 0
        bull_votes += 1 if m1_fast > 0 else 0
        bull_votes += 1 if m1_slow > 0 else 0
        bull_votes += 1 if m5 > 0 else 0
        bull_votes += 1 if ema_spread > 0 else 0
        bull_votes += 1 if rsi14 > 50 else 0
        bull_votes += 1 if candle_breadth > 0 else 0
        bull_votes += 1 if candle_body_bias > 0 else 0

        regime = "BULL" if bull_votes >= 5 else ("BEAR" if bull_votes <= 2 else "MIXED")

        text = (
            f"asset={asset_u} | regime={regime} votes={bull_votes}/7"
            f" | m1_fast={m1_fast:.3%}"
            f" | m1_slow={m1_slow:.3%}"
            f" | m5={m5:.3%}"
            f" | ema9-21={ema_spread:.3%}"
            f" | rsi14={rsi14:.1f}"
            f" | last25_up={up_candles} down={down_candles}"
            f" | last25_body={candle_body_bias:.3%}"
            f" | up_chance={prob*100:.1f}%"
        )
        return prob, text, None
    except Exception as e:
        return None, None, fmt(E_SIGNAL_PARSE, f"signal parse failed: {e}")
