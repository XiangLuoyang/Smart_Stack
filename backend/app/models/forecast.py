"""预测研究闭环的 ORM 模型。

涵盖市场数据批次、归一化日线、指数成分快照、交易日历、模型版本、
筛选运行、筛选候选、预测快照与复盘结果。

设计约束(见 docs/superpowers/specs):
- 正式预测、筛选排名、研究快照与复盘结果一旦写入不得原地修改;
- 观点变化通过新的证据/决策记录表达;
- 每份预测都必须具备统一期限、数据截止、模型版本与到期结果。
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPk


class MarketDataBatch(Base, UUIDPk, TimestampMixin):
    """一次冻结的行情数据批次:记录数据源、截止时间与校验和。"""

    __tablename__ = "market_data_batches"
    __table_args__ = (
        UniqueConstraint("business_date", "source", name="uq_batch_date_source"),
    )

    business_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    cutoff_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="SUCCESS", nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failures_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    universe_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("universe_snapshots.id"), nullable=True
    )


class DailyBar(Base, UUIDPk):
    """归一化日线:绑定批次,不可原地改写。"""

    __tablename__ = "daily_bars"
    __table_args__ = (
        UniqueConstraint(
            "market_data_batch_id", "symbol", "date",
            name="uq_dailybar_batch_symbol_date",
        ),
    )

    market_data_batch_id: Mapped[str] = mapped_column(
        ForeignKey("market_data_batches.id"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    adj_factor: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)


class UniverseSnapshot(Base, UUIDPk, TimestampMixin):
    """指数成分快照:记录某业务日某指数的全部成分。"""

    __tablename__ = "universe_snapshots"
    __table_args__ = (
        UniqueConstraint("business_date", "index_code", name="uq_universe_date_index"),
    )

    business_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    index_code: Mapped[str] = mapped_column(String(32), nullable=False)
    members_json: Mapped[str] = mapped_column(Text, nullable=False)


class TradingCalendar(Base, UUIDPk):
    """交易日历:每个交易日一行,session_date 唯一。"""

    __tablename__ = "trading_calendar"
    __table_args__ = (
        UniqueConstraint("session_date", name="uq_calendar_session_date"),
    )

    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)


class ModelVersion(Base, UUIDPk, TimestampMixin):
    """模型版本注册表:name + version 唯一。"""

    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_model_name_version"),
    )

    name: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    feature_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parameters_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    training_cutoff: Mapped[date | None] = mapped_column(Date, nullable=True)
    code_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ScreeningRun(Base, UUIDPk, TimestampMixin):
    """一次沪深300筛选运行:business_date + model_version 唯一。"""

    __tablename__ = "screening_runs"
    __table_args__ = (
        UniqueConstraint(
            "business_date", "model_version_id", name="uq_screening_date_model",
        ),
    )

    business_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    model_version_id: Mapped[str] = mapped_column(
        ForeignKey("model_versions.id"), nullable=False
    )
    market_data_batch_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_data_batches.id"), nullable=True
    )
    universe_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("universe_snapshots.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class ScreeningCandidate(Base, UUIDPk, TimestampMixin):
    """筛选候选:screening_run + symbol 唯一,关联预测快照。"""

    __tablename__ = "screening_candidates"
    __table_args__ = (
        UniqueConstraint(
            "screening_run_id", "symbol", name="uq_candidate_run_symbol",
        ),
    )

    screening_run_id: Mapped[str] = mapped_column(
        ForeignKey("screening_runs.id"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    prediction_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("prediction_snapshots.id"), nullable=True
    )


class PredictionSnapshot(Base, UUIDPk, TimestampMixin):
    """正式预测快照:business_date+symbol+model+horizon 唯一,追加式。"""

    __tablename__ = "prediction_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "business_date", "symbol", "model_version_id", "horizon_days",
            name="uq_prediction_date_symbol_model_horizon",
        ),
    )

    business_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    model_version_id: Mapped[str] = mapped_column(
        ForeignKey("model_versions.id"), nullable=False
    )
    market_data_batch_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_data_batches.id"), nullable=True
    )
    horizon_days: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    p_up: Mapped[float] = mapped_column(Float, nullable=False)
    p_flat: Mapped[float] = mapped_column(Float, nullable=False)
    p_down: Mapped[float] = mapped_column(Float, nullable=False)
    median_return: Mapped[float] = mapped_column(Float, nullable=False)
    lower_return: Mapped[float] = mapped_column(Float, nullable=False)
    upper_return: Mapped[float] = mapped_column(Float, nullable=False)
    expected_excess_return: Mapped[float] = mapped_column(Float, nullable=False)
    expected_mfe: Mapped[float] = mapped_column(Float, nullable=False)
    expected_mae: Mapped[float] = mapped_column(Float, nullable=False)
    state: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)


class ReviewResult(Base, UUIDPk, TimestampMixin):
    """到期复盘结果:prediction_snapshot 唯一,自动结算写入。"""

    __tablename__ = "review_results"
    __table_args__ = (
        UniqueConstraint("prediction_snapshot_id", name="uq_review_prediction"),
    )

    prediction_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("prediction_snapshots.id"), nullable=False, index=True
    )
    actual_return: Mapped[float | None] = mapped_column(Float, nullable=True)
    benchmark_excess: Mapped[float | None] = mapped_column(Float, nullable=True)
    signed_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    interval_coverage: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    mfe: Mapped[float | None] = mapped_column(Float, nullable=True)
    mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    direction_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    state: Mapped[str] = mapped_column(String(16), default="SETTLED", nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)