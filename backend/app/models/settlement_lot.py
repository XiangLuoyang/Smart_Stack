"""结算批次:T+1 可卖性追踪。

每次买入成交创建一个批次,记录获得日期、总数量、剩余数量与可卖日期。
卖出时按 FIFO 消耗最老的可卖批次。
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPk


class SettlementLot(Base, UUIDPk, TimestampMixin):
    __tablename__ = "settlement_lots"

    account_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("accounts.id"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    trade_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("trades.id"), nullable=False
    )
    acquired_date: Mapped[date] = mapped_column(Date, nullable=False)
    sellable_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    total_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_qty: Mapped[int] = mapped_column(Integer, nullable=False)