"""研究案例服务:创建案例(冻结分析)+ 追加证据/决策/复盘笔记。

核心契约:
- create_case 原子地创建案例与初始决策,并把当前分析快照以排序键 JSON 冻结;
- 所有 append_* 仅插入新行,绝不改写历史;关闭的案例拒绝追加(CASE_CLOSED);
- 决策通过 supersedes_id 链接到上一条决策,形成可追溯的观点演变链;
- 仅 ResearchCase.status 与 closed_at 允许更新(关闭案例)。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.forecast import PredictionSnapshot
from app.models.research import DecisionEntry, EvidenceEntry, ResearchCase, ReviewNote
from app.schemas.research import (
    CaseCreate,
    DecisionCreate,
    EvidenceCreate,
    ReviewNoteCreate,
)

logger = logging.getLogger(__name__)

VALID_DIRECTIONS = {"BULLISH", "NEUTRAL", "BEARISH"}
VALID_STANCES = {"SUPPORT", "OPPOSE", "NEUTRAL"}
VALID_ACTIONS = {"WATCH", "PLAN_BUY", "HOLD", "PLAN_SELL", "EXIT", "NO_ACTION"}


class ResearchDomainError(Exception):
    """研究领域错误,携带稳定错误码供上层映射。"""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(message or code)


class AnalysisReader:
    """分析快照读取器协议:返回某 symbol 的当前分析 payload(可注入)。"""

    def snapshot(self, symbol: str) -> dict:
        raise NotImplementedError


class SignalAnalysisReader(AnalysisReader):
    """生产用读取器:聚合信号源,LLM/信号失败绝不阻塞案例创建。"""

    def __init__(self, db: Session):
        self.db = db

    def snapshot(self, symbol: str) -> dict:
        signals: dict = {}
        try:
            from app.services.signal_service import SignalService

            signals = SignalService(self.db).get_all_sources(symbol)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"分析快照信号读取失败 {symbol}: {exc}")
        return {"symbol": symbol, "signals": signals}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ResearchService:
    """研究案例聚合服务。analysis_reader 可注入以便测试/回放。"""

    def __init__(self, db: Session, analysis_reader: AnalysisReader | None = None):
        self.db = db
        self.analysis_reader = analysis_reader or SignalAnalysisReader(db)

    def get_case(self, case_id: str) -> ResearchCase | None:
        return self.db.get(ResearchCase, case_id)

    def create_case(self, payload: CaseCreate) -> ResearchCase:
        prediction = self.db.get(PredictionSnapshot, payload.prediction_snapshot_id)
        if prediction is None:
            raise ResearchDomainError("PREDICTION_NOT_FOUND")

        direction = payload.direction.upper()
        if direction not in VALID_DIRECTIONS:
            raise ResearchDomainError("INVALID_DIRECTION")
        action = payload.action.upper()
        if action not in VALID_ACTIONS:
            raise ResearchDomainError("INVALID_ACTION")
        if not 1 <= payload.confidence <= 5:
            raise ResearchDomainError("INVALID_CONFIDENCE")
        if payload.expected_return_lower > payload.expected_return_upper:
            raise ResearchDomainError("INVALID_RETURN_RANGE")
        if direction == "BULLISH" and not (
            payload.stop_price < payload.planned_entry < payload.target_price
        ):
            raise ResearchDomainError("INVALID_PRICE_ORDER")

        snapshot = self.analysis_reader.snapshot(prediction.symbol)
        frozen = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, default=str)

        try:
            case = ResearchCase(
                symbol=prediction.symbol,
                prediction_snapshot_id=prediction.id,
                screening_candidate_id=payload.screening_candidate_id,
                status="ACTIVE",
                initial_direction=direction,
                thesis=payload.thesis,
                expected_return_lower=payload.expected_return_lower,
                expected_return_upper=payload.expected_return_upper,
                counterargument=payload.counterargument,
                invalidation_condition=payload.invalidation_condition,
                planned_entry=payload.planned_entry,
                target_price=payload.target_price,
                stop_price=payload.stop_price,
                confidence=payload.confidence,
                frozen_analysis_json=frozen,
            )
            self.db.add(case)
            self.db.flush()
            initial_decision = DecisionEntry(
                research_case_id=case.id,
                direction=direction,
                action=action,
                rationale=payload.thesis,
                confidence=payload.confidence,
            )
            self.db.add(initial_decision)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(case)
        return case

    def append_evidence(self, case_id: str, payload: EvidenceCreate) -> EvidenceEntry:
        case = self._require_open_case(case_id)
        stance = payload.stance.upper()
        if stance not in VALID_STANCES:
            raise ResearchDomainError("INVALID_STANCE")
        entry = EvidenceEntry(
            research_case_id=case.id,
            stance=stance,
            category=payload.category,
            content=payload.content,
            source_label=payload.source_label,
            source_url=payload.source_url,
            observed_date=payload.observed_date,
            created_by=payload.created_by,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def append_decision(self, case_id: str, payload: DecisionCreate) -> DecisionEntry:
        case = self._require_open_case(case_id)
        direction = payload.direction.upper()
        if direction not in VALID_DIRECTIONS:
            raise ResearchDomainError("INVALID_DIRECTION")
        action = payload.action.upper()
        if action not in VALID_ACTIONS:
            raise ResearchDomainError("INVALID_ACTION")
        if not 1 <= payload.confidence <= 5:
            raise ResearchDomainError("INVALID_CONFIDENCE")
        latest = self.db.scalars(
            select(DecisionEntry)
            .where(DecisionEntry.research_case_id == case.id)
            .order_by(DecisionEntry.created_at.desc())
            .limit(1)
        ).first()
        entry = DecisionEntry(
            research_case_id=case.id,
            direction=direction,
            action=action,
            rationale=payload.rationale,
            confidence=payload.confidence,
            supersedes_id=latest.id if latest else None,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def append_review_note(self, case_id: str, payload: ReviewNoteCreate) -> ReviewNote:
        case = self._require_open_case(case_id)
        note = ReviewNote(
            research_case_id=case.id,
            content=payload.content,
            attribution_json=payload.attribution_json,
            error_tags_json=payload.error_tags_json,
            created_by=payload.created_by,
        )
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    def close_case(self, case_id: str) -> ResearchCase:
        case = self.get_case(case_id)
        if case is None:
            raise ResearchDomainError("CASE_NOT_FOUND")
        if case.status != "CLOSED":
            case.status = "CLOSED"
            case.closed_at = _utcnow()
            self.db.commit()
            self.db.refresh(case)
        return case

    def _require_open_case(self, case_id: str) -> ResearchCase:
        case = self.get_case(case_id)
        if case is None:
            raise ResearchDomainError("CASE_NOT_FOUND")
        if case.status == "CLOSED":
            raise ResearchDomainError("CASE_CLOSED")
        return case