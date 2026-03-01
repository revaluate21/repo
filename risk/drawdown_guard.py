from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DrawdownGuard:
    daily_limit: float = -0.15
    max_limit: float = -0.40
    daily_pnl: float = 0.0
    equity_peak: float = 0.0
    current_equity: float = 0.0

    def update(self, equity: float, daily_pnl: float) -> None:
        self.current_equity = equity
        self.daily_pnl = daily_pnl
        self.equity_peak = max(self.equity_peak, equity)

    def should_halt(self) -> bool:
        max_dd = 0.0
        if self.equity_peak > 0:
            max_dd = (self.current_equity - self.equity_peak) / self.equity_peak
        return self.daily_pnl <= self.daily_limit or max_dd <= self.max_limit
