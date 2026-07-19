"""虚拟账户:资金 + 状态。"""
from __future__ import annotations

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPk


class Account(Base, UUIDPk, TimestampMixin):
    __tablename__ = "accounts"

    name: Mapped[str] = mapped_column(String(64), nullable=False)
    cash: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)
    # ACTIVE / FROZEN / CLOSED

    positions = relationship(
        "Position", back_populates="account", cascade="all, delete-orphan"
    )
    orders = relationship(
        "Order", back_populates="account", cascade="all, delete-orphan"
    )
    trades = relationship(
        "Trade", back_populates="account", cascade="all, delete-orphan"
    )
    risk_rule = relationship(
        "RiskRule", back_populates="account", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Account {self.name} cash={self.cash}>"
