from __future__ import annotations


def quote_two_sided(mid: float, spread_bps: float = 35) -> tuple[float, float]:
    half = spread_bps / 20000
    return max(0.01, mid * (1 - half)), min(0.99, mid * (1 + half))
