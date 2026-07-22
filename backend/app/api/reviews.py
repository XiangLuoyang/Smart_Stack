"""复盘结算路由:触发到期结算 + 查询预测/复盘状态 + 复盘笔记。"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.engine.trading_calendar import TradingCalendar
from app.models.forecast import PredictionSnapshot, ReviewResult
from app.models.research import ResearchCase, ReviewNote
from app.schemas.forecast import PredictionSnapshotRead
from app.schemas.review import ReviewResultRead, SettlementSummaryRead, SettleRequest
from app.services.review_service import DatabaseBarSource, ReviewService

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

VALID_ERROR_TAGS = {
    "MODEL_DIRECTION", "MODEL_MAGNITUDE", "THESIS", "TIMING",
    "EARLY_ENTRY", "LATE_ENTRY", "EARLY_EXIT", "LATE_EXIT",
    "DISCIPLINE", "DATA_QUALITY",
}


class ReviewNotePayload(BaseModel):
    attribution: str
    error_tags: list[str] = []
    discipline_followed: bool | None = None
    created_by: str | None = None


def get_bar_source(db: Session = Depends(get_db)) -> DatabaseBarSource:
    return DatabaseBarSource(db)


@router.post("/settle", response_model=SettlementSummaryRead)
def settle(
    payload: SettleRequest,
    db: Session = Depends(get_db),
    bar_source: DatabaseBarSource = Depends(get_bar_source),
):
    """结算所有截至 as_of 已到期的预测。"""
    svc = ReviewService(db, bar_source)
    return svc.settle_due(payload.as_of)


@router.get("", response_model=list[PredictionSnapshotRead])
def list_reviews(
    state: str | None = Query(default=None),
    as_of: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """按状态查询预测。state=DUE 返回已到期但尚未结算的预测(as_of 默认今日)。"""
    if state and state.upper() == "DUE":
        calendar = TradingCalendar(db)
        reference = as_of or date.today()
        candidates = db.scalars(
            select(PredictionSnapshot).where(
                PredictionSnapshot.state.in_(["PENDING", "PENDING_DATA"])
            )
        ).all()
        due: list[PredictionSnapshot] = []
        for pred in candidates:
            try:
                maturity = calendar.shift(pred.business_date, pred.horizon_days)
            except ValueError:
                continue
            if maturity <= reference:
                due.append(pred)
        return due

    stmt = select(PredictionSnapshot)
    if state:
        stmt = stmt.where(PredictionSnapshot.state == state.upper())
    stmt = stmt.order_by(PredictionSnapshot.business_date.desc())
    return list(db.scalars(stmt).all())


@router.get("/{prediction_id}")
def get_review_detail(prediction_id: str, db: Session = Depends(get_db)):
    """获取预测的复盘详情:自动结算结果 + 关联案例 + 复盘笔记。"""
    pred = db.get(PredictionSnapshot, prediction_id)
    if pred is None:
        raise HTTPException(status_code=404, detail="PREDICTION_NOT_FOUND")

    review = db.scalars(
        select(ReviewResult).where(
            ReviewResult.prediction_snapshot_id == prediction_id
        )
    ).first()

    cases = db.scalars(
        select(ResearchCase).where(
            ResearchCase.prediction_snapshot_id == prediction_id
        )
    ).all()

    notes: list[dict] = []
    for case in cases:
        for note in case.review_notes:
            notes.append({
                "id": note.id,
                "content": note.content,
                "attribution_json": note.attribution_json,
                "error_tags_json": note.error_tags_json,
                "created_by": note.created_by,
                "created_at": note.created_at.isoformat() if note.created_at else None,
            })

    return {
        "prediction_id": pred.id,
        "symbol": pred.symbol,
        "business_date": pred.business_date.isoformat(),
        "horizon_days": pred.horizon_days,
        "state": pred.state,
        "median_return": pred.median_return,
        "expected_excess_return": pred.expected_excess_return,
        "review": {
            "actual_return": review.actual_return,
            "benchmark_excess": review.benchmark_excess,
            "signed_error": review.signed_error,
            "interval_coverage": review.interval_coverage,
            "mfe": review.mfe,
            "mae": review.mae,
            "direction_correct": review.direction_correct,
            "state": review.state,
        } if review else None,
        "cases": [{"id": c.id, "thesis": c.thesis, "status": c.status} for c in cases],
        "notes": notes,
    }


@router.post("/{prediction_id}/notes", status_code=201)
def append_review_note(
    prediction_id: str,
    payload: ReviewNotePayload,
    db: Session = Depends(get_db),
):
    """向预测关联的研究案例追加复盘笔记(不修改自动结算结果)。"""
    pred = db.get(PredictionSnapshot, prediction_id)
    if pred is None:
        raise HTTPException(status_code=404, detail="PREDICTION_NOT_FOUND")

    invalid_tags = [t for t in payload.error_tags if t not in VALID_ERROR_TAGS]
    if invalid_tags:
        raise HTTPException(status_code=422, detail=f"INVALID_TAGS: {invalid_tags}")

    case = db.scalars(
        select(ResearchCase).where(
            ResearchCase.prediction_snapshot_id == prediction_id
        )
    ).first()
    if case is None:
        raise HTTPException(status_code=404, detail="NO_LINKED_CASE")

    import json
    attribution_data = {
        "attribution": payload.attribution,
        "discipline_followed": payload.discipline_followed,
    }
    note = ReviewNote(
        research_case_id=case.id,
        content=payload.attribution,
        attribution_json=json.dumps(attribution_data, ensure_ascii=False),
        error_tags_json=json.dumps(payload.error_tags, ensure_ascii=False),
        created_by=payload.created_by,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return {
        "id": note.id,
        "content": note.content,
        "attribution_json": note.attribution_json,
        "error_tags_json": note.error_tags_json,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }