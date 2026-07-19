from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SignalPayload(BaseModel):
    """单个信号源的有效载荷(松散结构)。"""
    score: float
    created_at: datetime


class SignalOut(BaseModel):
    symbol: str
    lstm: dict | None = None
    llm: dict | None = None
