from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class SimPosition:
    symbol: str
    side: str
    entry: float
    size: float


@dataclass
class SimulationEngine:
    balance: float
    slippage_min_bps: float = 40
    slippage_max_bps: float = 120
    positions: list[SimPosition] = field(default_factory=list)

    def apply_slippage(self, price: float, side: str) -> float:
        slip = random.uniform(self.slippage_min_bps, self.slippage_max_bps) / 10000
        return price * (1 + slip) if side == "BUY" else price * (1 - slip)

    def execute(self, symbol: str, side: str, price: float, size: float) -> dict:
        px = self.apply_slippage(price, side)
        cost = px * size
        if side == "BUY" and cost <= self.balance:
            self.balance -= cost
            self.positions.append(SimPosition(symbol, side, px, size))
        return {"symbol": symbol, "side": side, "fill_price": px, "size": size, "balance": self.balance}
