from __future__ import annotations

import asyncio
import json
import os
from collections import deque

import aiohttp


class BinanceWSClient:
    def __init__(self, symbols: list[str] | None = None) -> None:
        self.base = os.getenv("BINANCE_WS_URL", "wss://stream.binance.com:9443/stream")
        self.symbols = symbols or ["btcusdt", "ethusdt", "solusdt"]
        self.latest: dict[str, float] = {}
        self.history: dict[str, deque[float]] = {s: deque(maxlen=120) for s in self.symbols}

    async def stream(self) -> None:
        stream = "/".join(f"{s}@kline_1m" for s in self.symbols)
        url = f"{self.base}?streams={stream}"

        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(url, heartbeat=10) as ws:
                        async for msg in ws:
                            if msg.type != aiohttp.WSMsgType.TEXT:
                                continue
                            payload = json.loads(msg.data)
                            data = payload.get("data", {})
                            symbol = data.get("s", "").lower()
                            close = float(data.get("k", {}).get("c", 0))
                            if symbol and close:
                                self.latest[symbol] = close
                                self.history[symbol].append(close)
                            await asyncio.sleep(0)
            except Exception:
                await asyncio.sleep(2)
