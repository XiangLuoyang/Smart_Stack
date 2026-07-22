"""复盘结算相关 Pydantic schema(API 契约)。"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class SettlementSummaryRead(BaseModel):
    settled: int
    pending_data: int
    as_of: date


class SettleRequest(BaseModel):
    as_of: date


class ReviewResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    prediction_snapshot_id: str
    actual_return: float | None = None
    benchmark_excess: float | None = None
    signed_error: float | None = None
    interval_coverage: bool | None = None
    mfe: float | None = None
    mae: float | None = None
    direction_correct: bool | None = None
    state: str