from __future__ import annotations

import os

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential


class KalshiPublicClient:
    def __init__(self) -> None:
        self.base = os.getenv("KALSHI_BASE_URL", "https://trading-api.kalshi.com/trade-api/v2")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.2, max=2))
    async def fetch_event_price(self, ticker: str) -> float | None:
        url = f"{self.base}/markets/{ticker}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status != 200:
                    return None
                payload = await resp.json()
        yes_ask = payload.get("market", {}).get("yes_ask")
        return (yes_ask / 100) if yes_ask is not None else None
