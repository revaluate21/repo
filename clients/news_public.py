from __future__ import annotations

import re
import time
from dataclasses import dataclass

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass
class NewsItem:
    title: str
    ts: float


class NewsPublicClient:
    def __init__(self, feed_url: str = "https://www.coindesk.com/arc/outboundfeeds/rss/") -> None:
        self.feed_url = feed_url

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.2, max=2))
    async def fetch_latest(self, limit: int = 10) -> list[NewsItem]:
        async with aiohttp.ClientSession() as session:
            async with session.get(self.feed_url, timeout=8) as resp:
                if resp.status != 200:
                    return []
                text = await resp.text()

        titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>", text)
        clean_titles = []
        for a, b in titles:
            t = (a or b).strip()
            if t and "coindesk" not in t.lower():
                clean_titles.append(t)

        now = time.time()
        return [NewsItem(title=t, ts=now) for t in clean_titles[:limit]]
