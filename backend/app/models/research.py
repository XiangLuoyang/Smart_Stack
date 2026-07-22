"""研究闭环的 append-only ORM 模型。

涵盖研究案例(ResearchCase)及其证据(EvidenceEntry)、决策(DecisionEntry)、
复盘笔记(ReviewNote)三类追加式事件。

设计约束(见 docs/superpowers/specs):
- 研究案例创建时冻结当前分析快照(frozen_analysis_json),不得原地改写;
- 观点变化通过追加新的证据/决策记录表达,决策通过 supersedes_id 形成链;
- 仅 ResearchCase.status 与 closed_at 允许更新(关闭案例);
- 外键使用 RESTRICT,禁止删除仍被引用的预测/候选/案例。
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPk


def _utcnow() -> datetime:
    """微秒精度的 naive UTC 时间戳,保证追加事件可按 created_at 稳定排序。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ResearchCase(Base, UUIDPk, TimestampMixin):
    """研究案例:绑定一条正式预测,创建时冻结分析快照。"""

    __tablename__ = "research_cases"

    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    prediction_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("prediction_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    screening_candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("screening_candidates.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)
    initial_direction: Mapped[str] = mapped_column(String(16), nullable=False)
    thesis: Mapped[str] = mapped_column(Text, nullable=False)
    expected_return_lower: Mapped[float] = mapped_column(Float, nullable=False)
    expected_return_upper: Mapped[float] = mapped_column(Float, nullable=False)
    counterargument: Mapped[str] = mapped_column(Text, nullable=False)
    invalidation_condition: Mapped[str] = mapped_column(Text, nullable=False)
    planned_entry: Mapped[float] = mapped_column(Float, nullable=False)
    target_price: Mapped[float] = mapped_column(Float, nullable=False)
    stop_price: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    frozen_analysis_json: Mapped[str] = mapped_column(Text, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    prediction = relationship("PredictionSnapshot")
    screening_candidate = relationship("ScreeningCandidate")
    evidence_entries: Mapped[list["EvidenceEntry"]] = relationship(
        back_populates="research_case", order_by="EvidenceEntry.created_at"
    )
    decision_entries: Mapped[list["DecisionEntry"]] = relationship(
        back_populates="research_case", order_by="DecisionEntry.created_at"
    )
    review_notes: Mapped[list["ReviewNote"]] = relationship(
        back_populates="research_case", order_by="ReviewNote.created_at"
    )


class EvidenceEntry(Base, UUIDPk, TimestampMixin):
    """证据事件:支持/反对/中立的依据,追加式不可改写。"""

    __tablename__ = "evidence_entries"

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, server_default=func.current_timestamp(), nullable=False
    )

    research_case_id: Mapped[str] = mapped_column(
        ForeignKey("research_cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    stance: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    observed_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    research_case: Mapped[ResearchCase] = relationship(back_populates="evidence_entries")


class DecisionEntry(Base, UUIDPk, TimestampMixin):
    """决策事件:用户手动撰写的决策,通过 supersedes_id 形成链。"""

    __tablename__ = "decision_entries"

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, server_default=func.current_timestamp(), nullable=False
    )

    research_case_id: Mapped[str] = mapped_column(
        ForeignKey("research_cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    supersedes_id: Mapped[str | None] = mapped_column(
        ForeignKey("decision_entries.id", ondelete="RESTRICT"), nullable=True
    )

    research_case: Mapped[ResearchCase] = relationship(back_populates="decision_entries")


class ReviewNote(Base, UUIDPk, TimestampMixin):
    """复盘笔记:到期复盘时记录归因与误差标签。"""

    __tablename__ = "review_notes"

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, server_default=func.current_timestamp(), nullable=False
    )

    research_case_id: Mapped[str] = mapped_column(
        ForeignKey("research_cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    attribution_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_tags_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    research_case: Mapped[ResearchCase] = relationship(back_populates="review_notes")