from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    initial_cash: float = Field(default=1_000_000.0, gt=0)


class AccountOut(BaseModel):
    id: str
    name: str
    cash: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PositionOut(BaseModel):
    symbol: str
    qty: float
    avg_cost: float
    last_price: float | None = None
    market_value: float
    profit: float
    profit_pct: float
    stop_loss_price: float | None = None
    take_profit_price: float | None = None


class AccountOverview(BaseModel):
    account_id: str
    name: str
    cash: float
    status: str
    positions: list[PositionOut]
    total_market_value: float
    total_cost: float
    total_assets: float
    floating_profit: float
    floating_profit_pct: float
    updated_at: datetime
