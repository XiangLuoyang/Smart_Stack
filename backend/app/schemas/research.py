"""研究闭环 Pydantic schema(API 契约)。

仅定义写入侧契约(创建案例 / 追加证据 / 追加决策 / 复盘笔记)。
事件内容不可更新,因此没有对应的 Update schema。
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    """创建研究案例:绑定一条正式预测并给出初始决策。"""

    prediction_snapshot_id: str
    screening_candidate_id: str | None = None
    direction: str  # BULLISH / NEUTRAL / BEARISH
    thesis: str
    expected_return_lower: float
    expected_return_upper: float
    counterargument: str
    invalidation_condition: str
    planned_entry: float
    target_price: float
    stop_price: float
    confidence: int = Field(ge=1, le=5)
    action: str = "WATCH"  # 初始决策动作,默认观察


class EvidenceCreate(BaseModel):
    """追加一条证据事件。"""

    stance: str  # SUPPORT / OPPOSE / NEUTRAL
    category: str
    content: str
    source_label: str | None = None
    source_url: str | None = None
    observed_date: date
    created_by: str | None = None


class DecisionCreate(BaseModel):
    """追加一条决策事件(自动 supersede 上一条决策)。"""

    direction: str  # BULLISH / NEUTRAL / BEARISH
    action: str  # WATCH / PLAN_BUY / HOLD / PLAN_SELL / EXIT / NO_ACTION
    rationale: str
    confidence: int = Field(ge=1, le=5)


class ReviewNoteCreate(BaseModel):
    """追加一条复盘笔记。"""

    content: str
    attribution_json: str | None = None
    error_tags_json: str | None = None
    created_by: str | None = None