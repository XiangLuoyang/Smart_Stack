"""订单预留:冻结现金或股份直到订单成交/取消/拒绝。

每个待处理订单恰好一条预留;状态为 ACTIVE/RELEASED/CONSUMED。
"""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPk

RESERVATION_ACTIVE = "ACTIVE"
RESERVATION_RELEASED = "RELEASED"
RESERVATION_CONSUMED = "CONSUMED"


class OrderReservation(Base, UUIDPk, TimestampMixin):
    __tablename__ = "order_reservations"
    __table_args__ = (
        UniqueConstraint("order_id", "state", name="uq_reservation_order_active"),
    )

    order_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("orders.id"), nullable=False, index=True
    )
    account_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("accounts.id"), nullable=False, index=True
    )
    cash_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state: Mapped[str] = mapped_column(
        String(16), default=RESERVATION_ACTIVE, nullable=False
    )