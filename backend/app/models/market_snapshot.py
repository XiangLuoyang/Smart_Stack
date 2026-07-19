"""行情快照:每个标的每个时间点一行。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import UUIDPk


class MarketSnapshot(Base, UUIDPk):
    __tablename__ = "market_snapshots"
    __table_args__ = (
        Index("ix_snapshot_symbol_ts", "symbol", "ts"),
    )

    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # prev_close:用于涨跌幅计算
    prev_close: Mapped[float | None] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<MarketSnapshot {self.symbol} {self.ts} close={self.close}>"
