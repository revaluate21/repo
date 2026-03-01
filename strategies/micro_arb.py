from __future__ import annotations

from clients.polymarket_clob import MarketQuote


def detect_intra_market_edge(quote: MarketQuote, threshold: float = 0.982, fee_bps: float = 7, gas: float = 0.07) -> float:
    pair_cost = quote.yes_ask + quote.no_ask
    gross_edge = 1 - pair_cost
    fee = pair_cost * fee_bps / 10000
    net_edge = gross_edge - fee - gas / max(1, 100)
    return net_edge if pair_cost < threshold else 0.0
