# Polymarket + Cross-Venue Automation Suite

Aggressive research framework for simulation-first scalping, micro-arbitrage, and LP experimentation across Polymarket, Kalshi public odds, and crypto sentiment overlays.

## Features
- Async modular architecture (`clients/`, `strategies/`, `risk/`, `execution/`, `data/`, `dashboard/`)
- Polymarket CLOB client scaffold with EIP-712-ready env wiring
- Kalshi public market price fetches
- Binance public websocket stream for BTC/ETH/SOL 1m candles
- Intra-market arb, cross-venue convergence, bucket momentum, LP maker, sentiment velocity filters
- Fractional Kelly sizing, slippage model, latency guard, drawdown halt
- Simulation mode default; live mode gated behind explicit flags
- Rich terminal dashboard + Telegram alerts stub
- SQLite + CSV trade journaling

## Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run (Simulation)
```bash
python main.py --symbol BTC_EOD --kalshi-ticker INX-24DEC31-B5000 --balance 100
```

## Run (Live)
```bash
python main.py --live --confirm-live --symbol BTC_EOD --kalshi-ticker INX-24DEC31-B5000 --balance 100
```

## Known failure modes
- Kalshi endpoint schema changes can break field extraction.
- Polymarket auth flow is scaffolded and requires account-specific signing setup.
- Binance websocket may disconnect; add reconnect/backoff loop for production hardening.
- Slippage is modeled, not measured, and can be materially optimistic.
- Small-capital order sizes can fail min notional/lot constraints on some venues.
