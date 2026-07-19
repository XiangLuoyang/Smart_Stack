"""信号源:LSTM / LLM 等分析引擎的输出。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.models._mixins import UUIDPk

SOURCE_LSTM = "LSTM"
SOURCE_LLM = "LLM"


class Signal(Base, UUIDPk):
    __tablename__ = "signals"

    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<Signal {self.symbol} {self.source} score={self.score}>"
