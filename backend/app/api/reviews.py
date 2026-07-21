"""复盘结算路由:触发到期结算 + 查询预测/复盘状态。"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.engine.trading_calendar import TradingCalendar
from app.models.forecast import PredictionSnapshot
from app.schemas.forecast import PredictionSnapshotRead
from app.schemas.review import SettlementSummaryRead, SettleRequest
from app.services.review_service import DatabaseBarSource, ReviewService

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


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