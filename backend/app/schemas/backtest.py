from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BacktestRunRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    strategy_name: str = "ma_cross"
    params: dict[str, Any] = Field(default_factory=dict)
    start: datetime
    end: datetime
    initial_cash: float = Field(default=1_000_000.0, gt=0)


class BacktestRunOut(BaseModel):
    id: str
    strategy_name: str
    params_json: str
    start: datetime
    end: datetime
    metrics_json: str
    equity_curve_json: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
