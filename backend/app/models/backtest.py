"""回测:每次运行一条记录,关联多条成交明细。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPk


class BacktestRun(Base, UUIDPk, TimestampMixin):
    __tablename__ = "backtest_runs"

    strategy_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    params_json: Mapped[str] = mapped_column(Text, nullable=False)
    start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # 关键指标序列化为 JSON:net_value, total_return, sharpe, max_drawdown, win_rate, trade_count
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    # 净值曲线序列化为 JSON:[{"ts": "...", "nv": 1.0}, ...]
    equity_curve_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    trades = relationship(
        "BacktestTrade", back_populates="run", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<BacktestRun {self.strategy_name} {self.start}~{self.end}>"


class BacktestTrade(Base, UUIDPk):
    __tablename__ = "backtest_trades"

    run_id: Mapped[str] = mapped_column(String(32), ForeignKey("backtest_runs.id"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    run = relationship("BacktestRun", back_populates="trades")
