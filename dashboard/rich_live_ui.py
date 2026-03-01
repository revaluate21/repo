from __future__ import annotations

from rich.console import Console
from rich.table import Table


class LiveUI:
    def __init__(self) -> None:
        self.console = Console()

    def render(self, balance: float, pnl: float, latency_ms: float, alerts: list[str]) -> None:
        table = Table(title="Prediction-Market Bot")
        table.add_column("Metric")
        table.add_column("Value")
        table.add_row("Balance", f"{balance:.2f}")
        table.add_row("PNL", f"{pnl:.2%}")
        table.add_row("Latency", f"{latency_ms:.1f} ms")
        table.add_row("Alerts", " | ".join(alerts[-4:]) if alerts else "none")
        self.console.clear()
        self.console.print(table)
