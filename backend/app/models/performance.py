"""版本化性能指标 schema。

MetricBatch: 一次计算的版本/截止/状态;
PerformanceMetric: 按 scope(MODEL/SCREEN/USER/EXECUTION)和维度存储指标;
ModelEvaluationRun: 候选 vs 基线的 walk-forward 评估;
ModelPromotionDecision: 不可改写的晋升决策。
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPk


class MetricBatch(Base, UUIDPk, TimestampMixin):
    __tablename__ = "metric_batches"

    calculation_version: Mapped[str] = mapped_column(String(32), nullable=False)
    cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_row_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="SUCCESS")
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)


class PerformanceMetric(Base, UUIDPk, TimestampMixin):
    __tablename__ = "performance_metrics"
    __table_args__ = (
        UniqueConstraint(
            "batch_id", "scope", "scope_id", "metric_name", "dimension_key",
            name="uq_metric_identity",
        ),
    )

    batch_id: Mapped[str] = mapped_column(ForeignKey("metric_batches.id"), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    scope_id: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    dimension_key: Mapped[str] = mapped_column(String(32), default="ALL")
    dimension_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    numerator: Mapped[float | None] = mapped_column(Float, nullable=True)
    denominator: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class ModelEvaluationRun(Base, UUIDPk, TimestampMixin):
    __tablename__ = "model_evaluation_runs"

    candidate_model_id: Mapped[str] = mapped_column(String(32), nullable=False)
    baseline_model_id: Mapped[str] = mapped_column(String(32), nullable=False)
    folds_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")


class ModelPromotionDecision(Base, UUIDPk, TimestampMixin):
    __tablename__ = "model_promotion_decisions"

    evaluation_run_id: Mapped[str] = mapped_column(ForeignKey("model_evaluation_runs.id"), nullable=False)
    candidate_model_id: Mapped[str] = mapped_column(String(32), nullable=False)
    baseline_model_id: Mapped[str] = mapped_column(String(32), nullable=False)
    gate_decisions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)