"""订单:PENDING → FILLED / CANCELLED / REJECTED。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPk

# 订单状态机
ORDER_STATUS_PENDING = "PENDING"
ORDER_STATUS_FILLED = "FILLED"
ORDER_STATUS_CANCELLED = "CANCELLED"
ORDER_STATUS_REJECTED = "REJECTED"

# 订单方向
ORDER_SIDE_BUY = "BUY"
ORDER_SIDE_SELL = "SELL"

# 订单类型
ORDER_TYPE_MARKET = "MARKET"
ORDER_TYPE_LIMIT = "LIMIT"


class Order(Base, UUIDPk, TimestampMixin):
    __tablename__ = "orders"

    account_id: Mapped[str] = mapped_column(String(32), ForeignKey("accounts.id"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(8), nullable=False)  # BUY / SELL
    order_type: Mapped[str] = mapped_column(String(8), nullable=False)  # MARKET / LIMIT
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)  # 限价单的价格
    filled_qty: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    filled_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=ORDER_STATUS_PENDING, nullable=False, index=True)
    reject_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    filled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    account = relationship("Account", back_populates="orders")
    trades = relationship(
        "Trade", back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Order {self.side} {self.qty} {self.symbol} @{self.price} {self.status}>"
