from __future__ import annotations

import time
from dataclasses import dataclass

from clients.polymarket_clob import PolymarketCLOBClient


@dataclass
class ExecutorResult:
    ok: bool
    latency_ms: float
    payload: dict


class CLOBExecutor:
    def __init__(self, client: PolymarketCLOBClient, latency_guard_ms: int = 800):
        self.client = client
        self.latency_guard_ms = latency_guard_ms

    async def submit(self, symbol: str, side: str, price: float, size: float) -> ExecutorResult:
        start = time.perf_counter()
        payload = await self.client.place_limit_order(symbol, side, price, size)
        latency = (time.perf_counter() - start) * 1000
        if latency > self.latency_guard_ms:
            return ExecutorResult(ok=False, latency_ms=latency, payload={"error": "latency_guard"})
        return ExecutorResult(ok=True, latency_ms=latency, payload=payload)
