"""研究闭环 REST 端点:append-only,无 PATCH/DELETE。

错误映射:
- CASE_NOT_FOUND / PREDICTION_NOT_FOUND -> 404
- CASE_CLOSED -> 409
- 验证错误 -> 422
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.research import DecisionEntry, EvidenceEntry, ResearchCase, ReviewNote
from app.schemas.research import (
    CaseCreate,
    DecisionCreate,
    EvidenceCreate,
    ReviewNoteCreate,
)
from app.schemas.stock_research import StockResearchView
from app.services.research_service import ResearchDomainError, ResearchService
from app.services.stock_research_service import StockResearchService

router = APIRouter(prefix="/api/research", tags=["research"])


def _map_domain_error(exc: ResearchDomainError) -> HTTPException:
    if exc.code in ("CASE_NOT_FOUND", "PREDICTION_NOT_FOUND"):
        return HTTPException(status_code=404, detail=exc.code)
    if exc.code == "CASE_CLOSED":
        return HTTPException(status_code=409, detail=exc.code)
    return HTTPException(status_code=422, detail=exc.code)


# ---------------- 单股研究视图 ----------------


@router.get("/stocks/{symbol}", response_model=StockResearchView)
def get_stock_research(
    symbol: str,
    as_of: date | None = Query(None),
    db: Session = Depends(get_db),
):
    svc = StockResearchService(db)
    return svc.get(symbol, as_of=as_of)


# ---------------- 研究案例 CRUD(append-only) ----------------


@router.post("/cases", status_code=201)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    svc = ResearchService(db)
    try:
        case = svc.create_case(payload)
    except ResearchDomainError as exc:
        raise _map_domain_error(exc)
    return _case_to_dict(case)


@router.get("/cases")
def list_cases(
    symbol: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
):
    stmt = select(ResearchCase).order_by(ResearchCase.created_at.desc())
    if symbol:
        stmt = stmt.where(ResearchCase.symbol == symbol)
    if status:
        stmt = stmt.where(ResearchCase.status == status.upper())
    cases = db.scalars(stmt).all()
    return [_case_to_dict(c) for c in cases]


@router.get("/cases/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
    svc = ResearchService(db)
    case = svc.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="CASE_NOT_FOUND")
    return _case_to_dict(case, include_events=True)


@router.post("/cases/{case_id}/evidence", status_code=201)
def append_evidence(
    case_id: str, payload: EvidenceCreate, db: Session = Depends(get_db)
):
    svc = ResearchService(db)
    try:
        entry = svc.append_evidence(case_id, payload)
    except ResearchDomainError as exc:
        raise _map_domain_error(exc)
    return _evidence_to_dict(entry)


@router.post("/cases/{case_id}/decisions", status_code=201)
def append_decision(
    case_id: str, payload: DecisionCreate, db: Session = Depends(get_db)
):
    svc = ResearchService(db)
    try:
        entry = svc.append_decision(case_id, payload)
    except ResearchDomainError as exc:
        raise _map_domain_error(exc)
    return _decision_to_dict(entry)


@router.post("/cases/{case_id}/reviews", status_code=201)
def append_review_note(
    case_id: str, payload: ReviewNoteCreate, db: Session = Depends(get_db)
):
    svc = ResearchService(db)
    try:
        note = svc.append_review_note(case_id, payload)
    except ResearchDomainError as exc:
        raise _map_domain_error(exc)
    return _review_to_dict(note)


@router.post("/cases/{case_id}/close")
def close_case(case_id: str, db: Session = Depends(get_db)):
    svc = ResearchService(db)
    try:
        case = svc.close_case(case_id)
    except ResearchDomainError as exc:
        raise _map_domain_error(exc)
    return _case_to_dict(case)


# ---------------- Serializers ----------------


def _case_to_dict(case: ResearchCase, include_events: bool = False) -> dict:
    d = {
        "id": case.id,
        "symbol": case.symbol,
        "prediction_snapshot_id": case.prediction_snapshot_id,
        "screening_candidate_id": case.screening_candidate_id,
        "status": case.status,
        "initial_direction": case.initial_direction,
        "thesis": case.thesis,
        "expected_return_lower": case.expected_return_lower,
        "expected_return_upper": case.expected_return_upper,
        "counterargument": case.counterargument,
        "invalidation_condition": case.invalidation_condition,
        "planned_entry": case.planned_entry,
        "target_price": case.target_price,
        "stop_price": case.stop_price,
        "confidence": case.confidence,
        "frozen_analysis_json": case.frozen_analysis_json,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "closed_at": case.closed_at.isoformat() if case.closed_at else None,
    }
    if include_events:
        d["evidence_entries"] = [_evidence_to_dict(e) for e in case.evidence_entries]
        d["decision_entries"] = [_decision_to_dict(e) for e in case.decision_entries]
        d["review_notes"] = [_review_to_dict(n) for n in case.review_notes]
    return d


def _evidence_to_dict(e: EvidenceEntry) -> dict:
    return {
        "id": e.id,
        "research_case_id": e.research_case_id,
        "stance": e.stance,
        "category": e.category,
        "content": e.content,
        "source_label": e.source_label,
        "source_url": e.source_url,
        "observed_date": e.observed_date.isoformat() if e.observed_date else None,
        "created_by": e.created_by,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _decision_to_dict(e: DecisionEntry) -> dict:
    return {
        "id": e.id,
        "research_case_id": e.research_case_id,
        "direction": e.direction,
        "action": e.action,
        "rationale": e.rationale,
        "confidence": e.confidence,
        "supersedes_id": e.supersedes_id,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _review_to_dict(n: ReviewNote) -> dict:
    return {
        "id": n.id,
        "research_case_id": n.research_case_id,
        "content": n.content,
        "attribution_json": n.attribution_json,
        "error_tags_json": n.error_tags_json,
        "created_by": n.created_by,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }