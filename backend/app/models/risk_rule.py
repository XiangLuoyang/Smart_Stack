"""风控规则:每个账户一行。"""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPk


class RiskRule(Base, UUIDPk, TimestampMixin):
    __tablename__ = "risk_rules"

    account_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("accounts.id"), nullable=False, unique=True, index=True
    )
    # 最大总仓位占比(相对总资产),0~1
    max_position_pct: Mapped[float] = mapped_column(Float, default=0.9, nullable=False)
    # 单票最大仓位占比,0~1
    max_single_pct: Mapped[float] = mapped_column(Float, default=0.3, nullable=False)
    # 止损比例(相对成本价),如 0.08 表示跌 8% 触发
    stop_loss_pct: Mapped[float] = mapped_column(Float, default=0.08, nullable=False)
    # 止盈比例
    take_profit_pct: Mapped[float] = mapped_column(Float, default=0.20, nullable=False)
    # 单日最大交易次数(防止频繁交易)
    max_daily_trades: Mapped[int] = mapped_column(Integer, default=20, nullable=False)

    account = relationship("Account", back_populates="risk_rule")

    def __repr__(self) -> str:
        return f"<RiskRule max_single={self.max_single_pct} max_pos={self.max_position_pct}>"
