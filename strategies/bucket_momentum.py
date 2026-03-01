from __future__ import annotations

from dataclasses import dataclass

from risk.vol_filter import zscore_from_ema


@dataclass
class BucketSignal:
    side: str
    confidence: float
    tp_pct: float
    stop_pct: float


def build_bucket_signal(prices: list[float], imbalance: float, z_entry: float = 2.0) -> BucketSignal | None:
    if len(prices) < 20:
        return None
    z = zscore_from_ema(prices, span=3)
    if imbalance > 0.65:
        side = "BUY"
        return BucketSignal(side=side, confidence=min(1.0, imbalance), tp_pct=0.06, stop_pct=0.025)
    if abs(z) > z_entry:
        side = "SELL" if z > 0 else "BUY"
        return BucketSignal(side=side, confidence=min(1.0, abs(z) / 3), tp_pct=0.04, stop_pct=0.02)
    return None
