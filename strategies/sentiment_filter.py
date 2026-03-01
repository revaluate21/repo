from __future__ import annotations

import re
from collections import Counter, deque


class SentimentVelocity:
    def __init__(self, max_items: int = 300):
        self.items = deque(maxlen=max_items)
        self.positive = {"breakout", "surge", "approve", "bull", "launch"}
        self.negative = {"hack", "delay", "ban", "bear", "selloff"}

    def push(self, headline: str) -> None:
        tokens = re.findall(r"[a-zA-Z]+", headline.lower())
        self.items.append(tokens)

    def score(self) -> float:
        flat = [t for item in self.items for t in item]
        counts = Counter(flat)
        pos = sum(counts[w] for w in self.positive)
        neg = sum(counts[w] for w in self.negative)
        total = max(1, pos + neg)
        return (pos - neg) / total
