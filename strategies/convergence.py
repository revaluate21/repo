from __future__ import annotations


def cross_venue_edge(polymarket_prob: float, kalshi_prob: float | None, crypto_sent_delta: float, round_trip_cost: float = 0.018) -> float:
    if kalshi_prob is None:
        return 0.0
    raw = abs(polymarket_prob - kalshi_prob) + crypto_sent_delta
    return raw - round_trip_cost
