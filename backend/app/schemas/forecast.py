"""预测相关 Pydantic schema(API 契约)。"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class PredictionSnapshotRead(BaseModel):
    """正式预测快照的只读视图。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    business_date: date
    symbol: str
    model_version_id: str
    horizon_days: int
    p_up: float
    p_flat: float
    p_down: float
    median_return: float
    lower_return: float
    upper_return: float
    expected_excess_return: float
    expected_mfe: float
    expected_mae: float
    state: str


class ModelVersionRead(BaseModel):
    """模型版本的只读视图。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    version: str
    feature_version: str | None = None