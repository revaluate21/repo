from __future__ import annotations

import asyncio
import math
import random
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd


async def synthetic_brownian(symbol: str, hours: int = 48, start: float = 0.5, sigma: float = 0.02) -> pd.DataFrame:
    await asyncio.sleep(0)
    periods = hours * 60
    dt = 1 / (24 * 60)
    increments = np.random.normal(0, sigma * math.sqrt(dt), periods)
    prices = np.clip(start + np.cumsum(increments), 0.01, 0.99)
    start_t = datetime.now(tz=timezone.utc) - timedelta(minutes=periods)
    ts = [start_t + timedelta(minutes=i) for i in range(periods)]
    return pd.DataFrame({"timestamp": ts, "symbol": symbol, "price": prices})


async def replay_window(symbols: list[str], hours: int = 48) -> dict[str, pd.DataFrame]:
    data = {}
    for s in symbols:
        data[s] = await synthetic_brownian(s, hours=hours, start=random.uniform(0.2, 0.8))
    return data
