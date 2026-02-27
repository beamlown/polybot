from dataclasses import dataclass


@dataclass
class StrategyConfig:
    min_edge: float = 0.04


def fair_probability(signal_prob: float) -> float:
    # Placeholder for your model probability (0..1)
    return max(0.0, min(1.0, signal_prob))


def should_buy_yes(market_yes_price: float, model_prob: float, min_edge: float) -> bool:
    # Edge ≈ model fair prob - market implied prob
    edge = model_prob - market_yes_price
    return edge >= min_edge


def should_buy_no(market_yes_price: float, model_prob: float, min_edge: float) -> bool:
    # NO edge using yes-space: market_yes - model_prob
    edge = market_yes_price - model_prob
    return edge >= min_edge
