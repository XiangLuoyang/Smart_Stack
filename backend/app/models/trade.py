"""成交:每笔订单产生一条成交流水(纸面撮合无部分成交)。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPk


class Trade(Base, UUIDPk, TimestampMixin):
    __tablename__ = "trades"

    order_id: Mapped[str] = mapped_column(String(32), ForeignKey("orders.id"), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(String(32), ForeignKey("accounts.id"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    commission: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    stamp_duty: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    transfer_fee: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # total_cost: 买入时为正(现金流出),卖出时为负(现金流入),已扣/加费用
    total_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    filled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    order = relationship("Order", back_populates="trades")
    account = relationship("Account", back_populates="trades")

    def __repr__(self) -> str:
        return f"<Trade {self.side} {self.qty} {self.symbol} @{self.price}>"
