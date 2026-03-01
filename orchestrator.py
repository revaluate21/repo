from __future__ import annotations

import argparse
import asyncio
import csv
import time
import contextlib
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiosqlite
import yaml
from dotenv import load_dotenv

from clients.binance_ws import BinanceWSClient
from clients.kalshi_public import KalshiPublicClient
from clients.polymarket_clob import PolymarketCLOBClient
from config.schema import Settings
from dashboard.rich_live_ui import LiveUI
from dashboard.telegram_alerts import TelegramAlerts
from execution.clob_executor import CLOBExecutor
from execution.simulation_engine import SimulationEngine
from risk.drawdown_guard import DrawdownGuard
from risk.position_sizer import fractional_kelly_size
from strategies.bucket_momentum import build_bucket_signal
from strategies.convergence import cross_venue_edge
from strategies.lp_maker import quote_two_sided
from strategies.micro_arb import detect_intra_market_edge
from strategies.sentiment_filter import SentimentVelocity


async def init_db(path: str) -> None:
    async with aiosqlite.connect(path) as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS trades (
            ts REAL, symbol TEXT, side TEXT, price REAL, size REAL, mode TEXT, note TEXT
            )"""
        )
        await db.commit()


async def log_trade(db_path: str, csv_path: str, row: dict[str, Any]) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO trades(ts,symbol,side,price,size,mode,note) VALUES(?,?,?,?,?,?,?)",
            (row["ts"], row["symbol"], row["side"], row["price"], row["size"], row["mode"], row["note"]),
        )
        await db.commit()
    path = Path(csv_path)
    write_header = not path.exists()
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ts", "symbol", "side", "price", "size", "mode", "note"])
        if write_header:
            writer.writeheader()
        writer.writerow(row)


@dataclass
class RuntimeControl:
    mode: str = "simulation"
    enabled_strategies: dict[str, bool] = field(
        default_factory=lambda: {
            "micro_arb": True,
            "bucket_momentum": True,
            "lp_maker": True,
            "sentiment": True,
            "convergence": True,
        }
    )
    paused: bool = False
    confirm_text: str = ""
    live_confirmed: bool = False


class BotController:
    def __init__(self, symbol: str = "BTC_EOD", kalshi_ticker: str = "INX-24DEC31-B5000", balance: float = 100.0):
        load_dotenv()
        with open("config/settings.yaml", "r", encoding="utf-8") as f:
            self.settings = Settings.model_validate(yaml.safe_load(f))

        self.symbol = symbol
        self.kalshi_ticker = kalshi_ticker
        self.start_balance = balance
        self.balance = balance
        self.pnl = 0.0
        self.runtime = RuntimeControl(mode="simulation")
        self.running = False

        self.pm = PolymarketCLOBClient()
        self.kalshi = KalshiPublicClient()
        self.binance = BinanceWSClient()
        self.executor = CLOBExecutor(self.pm, latency_guard_ms=self.settings.latency_guard_ms)
        self.sim = SimulationEngine(balance=balance)
        self.ui = LiveUI()
        self.alerts = TelegramAlerts()
        self.sent = SentimentVelocity()
        self.guard = DrawdownGuard(self.settings.risk.daily_drawdown_limit, self.settings.risk.max_drawdown_limit)

        self.db_path = "trades.db"
        self.csv_path = "trade_journal.csv"
        self.log_buffer: deque[str] = deque(maxlen=300)
        self.trade_buffer: deque[dict[str, Any]] = deque(maxlen=200)
        self.last_latency_ms = 0.0
        self._loop_task: asyncio.Task[Any] | None = None
        self._binance_task: asyncio.Task[Any] | None = None

    async def start(self, live: bool = False, live_phrase: str = "") -> None:
        if self.running:
            return
        self.runtime.mode = "live" if live else "simulation"
        if live:
            self.runtime.live_confirmed = live_phrase.strip() == "I UNDERSTAND I CAN LOSE EVERYTHING"
            if not self.runtime.live_confirmed:
                raise ValueError("Live mode confirmation phrase invalid")
        await init_db(self.db_path)
        self.running = True
        if self._binance_task is None or self._binance_task.done():
            self._binance_task = asyncio.create_task(self.binance.stream())
        self._loop_task = asyncio.create_task(self._run_loop())
        self.log("bot started")

    async def stop(self) -> None:
        self.running = False
        if self._loop_task:
            self._loop_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._loop_task
        self.log("bot stopped")

    def pause(self, value: bool) -> None:
        self.runtime.paused = value
        self.log(f"paused={value}")

    def update_strategy(self, name: str, enabled: bool) -> None:
        if name in self.runtime.enabled_strategies:
            self.runtime.enabled_strategies[name] = enabled
            self.log(f"strategy {name}={enabled}")

    def set_wallet(self, private_key: str = "", mnemonic: str = "") -> None:
        # In-memory only: do not persist wallet credentials.
        if private_key:
            self.pm.private_key = private_key
        if mnemonic:
            self.pm.private_key = f"mnemonic:{mnemonic[:8]}..."
        self.log("wallet loaded in memory")

    def status(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "mode": self.runtime.mode,
            "balance": self.balance,
            "pnl": self.pnl,
            "latency_ms": self.last_latency_ms,
            "strategies": self.runtime.enabled_strategies,
            "paused": self.runtime.paused,
            "logs": list(self.log_buffer)[-25:],
            "recent_trades": list(self.trade_buffer)[-20:],
        }

    async def fetch_journal(self, limit: int = 200) -> list[dict[str, Any]]:
        await init_db(self.db_path)
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT ts,symbol,side,price,size,mode,note FROM trades ORDER BY ts DESC LIMIT ?",
                (limit,),
            )
            rows = await cur.fetchall()
        return [
            {"ts": r[0], "symbol": r[1], "side": r[2], "price": r[3], "size": r[4], "mode": r[5], "note": r[6]}
            for r in rows
        ]

    def log(self, message: str) -> None:
        self.log_buffer.append(f"{time.strftime('%H:%M:%S')} | {message}")

    async def manual_trade(self, side: str, price: float, size: float) -> dict[str, Any]:
        if self.runtime.mode == "live":
            res = await self.executor.submit(self.symbol, side, price, size)
            self.last_latency_ms = res.latency_ms
            payload = res.payload
        else:
            payload = self.sim.execute(self.symbol, side, price, size)
            self.balance = self.sim.balance
            self.last_latency_ms = 20.0

        row = {
            "ts": time.time(),
            "symbol": self.symbol,
            "side": side,
            "price": price,
            "size": size,
            "mode": self.runtime.mode,
            "note": "manual",
        }
        await log_trade(self.db_path, self.csv_path, row)
        self.trade_buffer.appendleft(row)
        self.log(f"manual {side} {size:.2f} @ {price:.4f}")
        return payload

    async def _run_loop(self) -> None:
        while self.running:
            if self.runtime.paused:
                await asyncio.sleep(0.25)
                continue

            quote = await self.pm.get_market_quote(self.symbol)
            micro_edge = (
                detect_intra_market_edge(
                    quote,
                    threshold=self.settings.strategies.intra_polymarket_arb_threshold,
                    fee_bps=self.settings.fees.clob_fee_bps,
                    gas=self.settings.fees.gas_cost_usdc,
                )
                if self.runtime.enabled_strategies["micro_arb"]
                else 0.0
            )

            kalshi_px = await self.kalshi.fetch_event_price(self.kalshi_ticker)
            crypto_delta = 0.0
            if self.binance.history["btcusdt"]:
                pxs = list(self.binance.history["btcusdt"])
                crypto_delta = (pxs[-1] - pxs[0]) / max(pxs[0], 1e-9)
            cross_edge = (
                cross_venue_edge(quote.yes_ask, kalshi_px, crypto_delta, self.settings.strategies.cross_venue_edge_threshold)
                if self.runtime.enabled_strategies["convergence"]
                else 0.0
            )

            if self.runtime.enabled_strategies["sentiment"]:
                self.sent.push("btc breakout rumors after macro print")
                confidence_boost = max(
                    -self.settings.strategies.sentiment_boost_max,
                    min(self.settings.strategies.sentiment_boost_max, self.sent.score()),
                )
            else:
                confidence_boost = 0.0

            signal = (
                build_bucket_signal(list(self.binance.history["btcusdt"]), imbalance=0.7 + confidence_boost)
                if self.runtime.enabled_strategies["bucket_momentum"]
                else None
            )
            total_edge = max(0.0, micro_edge) + max(0.0, cross_edge)
            size = fractional_kelly_size(
                balance=self.balance,
                edge=max(0.01, total_edge),
                win_prob=min(0.95, 0.55 + total_edge),
                fractional_kelly=self.settings.risk.fractional_kelly,
                cap=self.settings.risk.max_balance_fraction_per_trade,
            )

            if signal and size > 0:
                if self.runtime.mode == "live":
                    res = await self.executor.submit(self.symbol, signal.side, quote.yes_ask, size)
                    self.last_latency_ms = res.latency_ms
                    ok = res.ok
                else:
                    fill = self.sim.execute(self.symbol, signal.side, quote.yes_ask, size)
                    self.balance = fill["balance"]
                    self.last_latency_ms = 20.0
                    ok = True

                row = {
                    "ts": time.time(),
                    "symbol": self.symbol,
                    "side": signal.side,
                    "price": quote.yes_ask,
                    "size": size,
                    "mode": self.runtime.mode,
                    "note": f"edge={total_edge:.4f}",
                }
                await log_trade(self.db_path, self.csv_path, row)
                self.trade_buffer.appendleft(row)
                if ok:
                    self.log(f"exec {signal.side} size={size:.2f} edge={total_edge:.4f}")
                bid, ask = quote_two_sided((quote.yes_bid + quote.yes_ask) / 2)
                self.log(f"lp quote {bid:.3f}/{ask:.3f}")

            self.pnl = (self.balance - self.start_balance) / self.start_balance
            self.guard.update(self.balance, self.pnl)
            if self.guard.should_halt():
                self.log("trading halted by drawdown guard")
                self.running = False
                break

            await asyncio.sleep(max(0.125, 1 / self.settings.refresh_hz))


async def run(args: argparse.Namespace) -> None:
    bot = BotController(symbol=args.symbol, kalshi_ticker=args.kalshi_ticker, balance=args.balance)
    await bot.start(live=args.live, live_phrase="I UNDERSTAND I CAN LOSE EVERYTHING" if args.confirm_live else "")
    while bot.running:
        bot.ui.render(balance=bot.balance, pnl=bot.pnl, latency_ms=bot.last_latency_ms, alerts=bot.status()["logs"])
        await asyncio.sleep(0.5)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--live", action="store_true")
    p.add_argument("--confirm-live", action="store_true")
    p.add_argument("--symbol", default="BTC_EOD")
    p.add_argument("--kalshi-ticker", default="INX-24DEC31-B5000")
    p.add_argument("--balance", type=float, default=100)
    return p.parse_args()

