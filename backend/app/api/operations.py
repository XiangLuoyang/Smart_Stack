"""模拟操作 API:preview/confirm 两步下单 + 单账户查询。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.engine.matching import Quote
from app.models.account import Account
from app.models.order_preview import OrderPreview
from app.services.order_confirmation_service import ConfirmationError, OrderConfirmationService

router = APIRouter(prefix="/api/orders", tags=["operations"])


class PreviewRequest(BaseModel):
    account_id: str
    symbol: str
    side: str
    qty: int
    order_type: str = "MARKET"
    price: float | None = None
    research_case_id: str | None = None
    decision_entry_id: str | None = None


class ConfirmRequest(BaseModel):
    preview_id: str
    confirmation_token: str
    idempotency_key: str


def _map_error(exc: ConfirmationError) -> HTTPException:
    if exc.code in ("PREVIEW_NOT_FOUND",):
        return HTTPException(status_code=404, detail=exc.code)
    if exc.code in ("PREVIEW_EXPIRED", "ALREADY_CONFIRMED", "INVALID_TOKEN"):
        return HTTPException(status_code=409, detail=exc.code)
    return HTTPException(status_code=422, detail=exc.code)


@router.post("/preview")
def preview_order(payload: PreviewRequest, db: Session = Depends(get_db)):
    svc = OrderConfirmationService(db)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    quote = Quote(symbol=payload.symbol, price=payload.price or 10.0, ts=now)
    try:
        p = svc.preview(
            account_id=payload.account_id,
            symbol=payload.symbol,
            side=payload.side,
            qty=payload.qty,
            order_type=payload.order_type,
            price=payload.price,
            research_case_id=payload.research_case_id,
            decision_entry_id=payload.decision_entry_id,
            quote=quote,
        )
    except ConfirmationError as exc:
        raise _map_error(exc)
    return {
        "id": p.id,
        "confirmation_token": p.confirmation_token,
        "expires_at": p.expires_at.isoformat(),
        "fee_estimate": p.fee_estimate,
        "symbol": p.symbol,
        "side": p.side,
        "qty": p.qty,
    }


@router.post("/confirm", status_code=201)
def confirm_order(payload: ConfirmRequest, db: Session = Depends(get_db)):
    svc = OrderConfirmationService(db)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    preview = db.get(OrderPreview, payload.preview_id)
    quote = None
    if preview and preview.quote_price:
        quote = Quote(symbol=preview.symbol, price=preview.quote_price, ts=preview.quote_ts or now)
    try:
        result = svc.confirm(
            preview_id=payload.preview_id,
            confirmation_token=payload.confirmation_token,
            idempotency_key=payload.idempotency_key,
            quote=quote,
        )
    except ConfirmationError as exc:
        raise _map_error(exc)
    return result