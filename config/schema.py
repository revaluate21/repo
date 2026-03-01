from pydantic import BaseModel, Field


class FeeConfig(BaseModel):
    clob_fee_bps: float = Field(default=7)
    gas_cost_usdc: float = Field(default=0.07)


class RiskConfig(BaseModel):
    fractional_kelly: float = Field(default=0.25, ge=0.1, le=0.5)
    max_balance_fraction_per_trade: float = Field(default=0.25, gt=0, le=0.25)
    daily_drawdown_limit: float = Field(default=-0.15)
    max_drawdown_limit: float = Field(default=-0.4)


class StrategyConfig(BaseModel):
    intra_polymarket_arb_threshold: float = 0.982
    cross_venue_edge_threshold: float = 0.018
    imbalance_threshold: float = 0.65
    zscore_entry_threshold: float = 2.0
    tp_pct_range: tuple[float, float] = (0.03, 0.12)
    stop_pct_range: tuple[float, float] = (0.015, 0.04)
    sentiment_boost_max: float = 0.15


class Settings(BaseModel):
    mode: str = "simulation"
    refresh_hz: int = 5
    orderbook_levels: int = 8
    latency_guard_ms: int = 800
    fees: FeeConfig = FeeConfig()
    risk: RiskConfig = RiskConfig()
    strategies: StrategyConfig = StrategyConfig()
