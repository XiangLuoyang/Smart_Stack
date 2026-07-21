"""筛选运行相关 Pydantic schema(API 契约)。"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ScreeningCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    symbol: str
    rank: int
    score: float
    status: str
    failure_reason: str | None = None
    prediction_snapshot_id: str | None = None


class ScreeningRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_date: date
    model_version_id: str
    model_version: str | None = None
    status: str
    total_count: int
    success_count: int
    failure_count: int
    data_cutoff: datetime | None = None
    candidates: list[ScreeningCandidateRead] = []
    top10: list[ScreeningCandidateRead] = []