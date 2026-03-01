from __future__ import annotations

import numpy as np


def realized_vol(prices: list[float]) -> float:
    if len(prices) < 3:
        return 0.0
    arr = np.array(prices)
    rets = np.diff(np.log(arr))
    return float(np.std(rets) * (len(rets) ** 0.5))


def zscore_from_ema(prices: list[float], span: int = 3) -> float:
    if len(prices) < 10:
        return 0.0
    arr = np.array(prices)
    alpha = 2 / (span + 1)
    ema = arr[0]
    for p in arr[1:]:
        ema = alpha * p + (1 - alpha) * ema
    std = arr[-10:].std() or 1e-6
    return float((arr[-1] - ema) / std)
