from __future__ import annotations

from pydantic import BaseModel, Field


class RiskRuleOut(BaseModel):
    account_id: str
    max_position_pct: float
    max_single_pct: float
    stop_loss_pct: float
    take_profit_pct: float
    max_daily_trades: int

    model_config = {"from_attributes": True}


class RiskRuleUpdate(BaseModel):
    max_position_pct: float | None = Field(default=None, ge=0, le=1)
    max_single_pct: float | None = Field(default=None, ge=0, le=1)
    stop_loss_pct: float | None = Field(default=None, ge=0, le=1)
    take_profit_pct: float | None = Field(default=None, ge=0, le=1)
    max_daily_trades: int | None = Field(default=None, ge=1, le=1000)
