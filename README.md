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

## Run (CLI Simulation)
```bash
python main.py --symbol BTC_EOD --kalshi-ticker INX-24DEC31-B5000 --balance 100
```

## Run (CLI Live)
```bash
python main.py --live --confirm-live --symbol BTC_EOD --kalshi-ticker INX-24DEC31-B5000 --balance 100
```

## Web App Mode
Run everything (backend + UI) in one command:

```bash
pip install -r requirements.txt && python run_app.py
```

This launches a local FastAPI + HTMX + Tailwind terminal-style interface at `http://127.0.0.1:8000` and opens your browser automatically.

### UI flow
1. **Overview panel**: live mode/balance/PNL/latency cards update through WebSocket plus HTMX polling fallback.
2. **Control center**: start/stop/pause bot, including strict live confirmation phrase (`I UNDERSTAND I CAN LOSE EVERYTHING`).
3. **Wallet connect card**: private key/mnemonic memory-only form with local-only warning banner.
4. **Strategy toggles**: one-click ON/OFF for micro-arb, bucket momentum, LP maker, sentiment, convergence.
5. **Manual execution**: side/price/size form with immediate journal logging.
6. **Settings**: runtime refresh/risk controls editable from UI.
7. **Journal viewer**: live-updating SQLite table and CSV export endpoint.
8. **Live logs**: streaming event feed for executions, LP quotes, and guard-trigger alerts.

## Known failure modes
- Kalshi endpoint schema changes can break field extraction.
- Polymarket auth flow is scaffolded and requires account-specific signing setup.
- Binance websocket may disconnect; add reconnect/backoff loop for production hardening.
- Slippage is modeled, not measured, and can be materially optimistic.
- Small-capital order sizes can fail min notional/lot constraints on some venues.
