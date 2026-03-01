from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class OrderBookLevel:
    price: float
    size: float


@dataclass
class OrderBookSnapshot:
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    ts: float = field(default_factory=lambda: time.time())


class OrderBookCache:
    def __init__(self, levels: int = 8):
        self._levels = levels
        self._cache: dict[str, OrderBookSnapshot] = {}
        self._lock = asyncio.Lock()

    async def update(self, symbol: str, bids: list[tuple[float, float]], asks: list[tuple[float, float]]) -> None:
        async with self._lock:
            self._cache[symbol] = OrderBookSnapshot(
                bids=[OrderBookLevel(*x) for x in bids[: self._levels]],
                asks=[OrderBookLevel(*x) for x in asks[: self._levels]],
            )

    async def get(self, symbol: str) -> OrderBookSnapshot | None:
        async with self._lock:
            return self._cache.get(symbol)

    async def symbols(self) -> list[str]:
        async with self._lock:
            return list(self._cache.keys())
