from __future__ import annotations

import argparse
import asyncio
import csv
import time
from pathlib import Path

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


async def log_trade(db_path: str, csv_path: str, row: dict) -> None:
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


async def run(args: argparse.Namespace) -> None:
    load_dotenv()
    with open("config/settings.yaml", "r", encoding="utf-8") as f:
        settings = Settings.model_validate(yaml.safe_load(f))

    mode = "live" if args.live else settings.mode
    if mode == "live" and not args.confirm_live:
        raise SystemExit("Live mode requires --confirm-live")

    pm = PolymarketCLOBClient()
    kalshi = KalshiPublicClient()
    binance = BinanceWSClient()
    executor = CLOBExecutor(pm, latency_guard_ms=settings.latency_guard_ms)
    sim = SimulationEngine(balance=args.balance)
    ui = LiveUI()
    alerts = TelegramAlerts()
    sent = SentimentVelocity()
    guard = DrawdownGuard(settings.risk.daily_drawdown_limit, settings.risk.max_drawdown_limit)

    db_path = args.db_path
    csv_path = args.csv_path
    await init_db(db_path)
    asyncio.create_task(binance.stream())

    balance = args.balance
    start_balance = balance
    symbol = args.symbol

    while True:
        quote = await pm.get_market_quote(symbol)
        micro_edge = detect_intra_market_edge(
            quote,
            threshold=settings.strategies.intra_polymarket_arb_threshold,
            fee_bps=settings.fees.clob_fee_bps,
            gas=settings.fees.gas_cost_usdc,
        )

        kalshi_px = await kalshi.fetch_event_price(args.kalshi_ticker)
        crypto_delta = 0.0
        if binance.history["btcusdt"]:
            pxs = list(binance.history["btcusdt"])
            crypto_delta = (pxs[-1] - pxs[0]) / max(pxs[0], 1e-9)
        cross_edge = cross_venue_edge(quote.yes_ask, kalshi_px, crypto_delta, settings.strategies.cross_venue_edge_threshold)

        sent.push("btc breakout rumors after macro print")
        confidence_boost = max(-settings.strategies.sentiment_boost_max, min(settings.strategies.sentiment_boost_max, sent.score()))

        signal = build_bucket_signal(list(binance.history["btcusdt"]), imbalance=0.7 + confidence_boost)
        total_edge = max(0.0, micro_edge) + max(0.0, cross_edge)
        size = fractional_kelly_size(
            balance=balance,
            edge=max(0.01, total_edge),
            win_prob=min(0.95, 0.55 + total_edge),
            fractional_kelly=settings.risk.fractional_kelly,
            cap=settings.risk.max_balance_fraction_per_trade,
        )

        alerts_text: list[str] = []
        if signal and size > 0:
            if mode == "live":
                res = await executor.submit(symbol, signal.side, quote.yes_ask, size)
                ok = res.ok
                latency = res.latency_ms
            else:
                fill = sim.execute(symbol, signal.side, quote.yes_ask, size)
                balance = fill["balance"]
                ok = True
                latency = 20.0

            row = {
                "ts": time.time(),
                "symbol": symbol,
                "side": signal.side,
                "price": quote.yes_ask,
                "size": size,
                "mode": mode,
                "note": f"edge={total_edge:.4f}",
            }
            await log_trade(db_path, csv_path, row)
            if ok:
                alerts_text.append(f"Executed {signal.side} {symbol} size={size:.2f}")

            bid, ask = quote_two_sided((quote.yes_bid + quote.yes_ask) / 2)
            alerts_text.append(f"LP quote: {bid:.3f}/{ask:.3f}")
            await alerts.send("; ".join(alerts_text))
        else:
            latency = 0.0

        pnl = (balance - start_balance) / start_balance
        guard.update(balance, pnl)
        if guard.should_halt():
            await alerts.send("Trading halted by drawdown guard")
            break

        ui.render(balance=balance, pnl=pnl, latency_ms=latency, alerts=alerts_text)
        await asyncio.sleep(max(0.125, 1 / settings.refresh_hz))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--live", action="store_true")
    p.add_argument("--confirm-live", action="store_true")
    p.add_argument("--symbol", default="BTC_EOD")
    p.add_argument("--kalshi-ticker", default="INX-24DEC31-B5000")
    p.add_argument("--balance", type=float, default=100)
    p.add_argument("--db-path", default="trades.db")
    p.add_argument("--csv-path", default="trade_journal.csv")
    return p.parse_args()
