from __future__ import annotations


def fractional_kelly_size(balance: float, edge: float, win_prob: float, fractional_kelly: float, cap: float) -> float:
    loss_prob = max(0.0, 1.0 - win_prob)
    if edge <= 0 or win_prob <= 0:
        return 0.0
    raw_kelly = max(0.0, (edge * win_prob - loss_prob) / max(edge, 1e-6))
    frac = min(cap, max(0.0, raw_kelly * fractional_kelly))
    return balance * frac
