"""持仓:仅多头,不支持融券。一个账户一个标的一行。"""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPk


class Position(Base, UUIDPk, TimestampMixin):
    __tablename__ = "positions"
    __table_args__ = (UniqueConstraint("account_id", "symbol", name="uq_position_account_symbol"),)

    account_id: Mapped[str] = mapped_column(String(32), ForeignKey("accounts.id"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    qty: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reserved_qty: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # avg_cost: 加权平均成本(不含费用),用于浮动盈亏计算
    avg_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # stop_loss / take_profit: 用户设置的止损止盈价,NULL 表示未设置
    stop_loss_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    take_profit_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    account = relationship("Account", back_populates="positions")

    @property
    def market_value(self) -> float:
        """需要外部注入 last_price,默认用 avg_cost 占位。"""
        return self.qty * self.avg_cost

    def __repr__(self) -> str:
        return f"<Position {self.symbol} qty={self.qty} cost={self.avg_cost}>"
