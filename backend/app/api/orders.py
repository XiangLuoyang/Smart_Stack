"""订单路由:下单、撤单、查询。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_market_service_with_db
from app.schemas.order import OrderCreate, OrderOut, PlaceOrderResultOut, TradeOut
from app.services.market_service import MarketService
from app.services.order_service import OrderService

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=PlaceOrderResultOut)
def place_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    market: MarketService = Depends(get_market_service_with_db),
):
    quote = market.get_quote(payload.symbol)
    svc = OrderService(db)
    result = svc.place(
        account_id=payload.account_id,
        symbol=payload.symbol,
        side=payload.side,
        qty=payload.qty,
        order_type=payload.order_type,
        price=payload.price,
        quote=quote,
    )
    if not result.accepted and result.order.id is None:
        raise HTTPException(400, result.message)
    return PlaceOrderResultOut(
        accepted=result.accepted,
        message=result.message,
        order=result.order,
        trade=result.trade,
    )


@router.delete("/{order_id}")
def cancel_order(order_id: str, db: Session = Depends(get_db)):
    ok, msg = OrderService(db).cancel(order_id)
    if not ok:
        raise HTTPException(400, msg)
    return {"ok": True, "message": msg}


@router.get("", response_model=list[OrderOut])
def list_orders(
    account_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return OrderService(db).list_orders(account_id=account_id, status=status)


@router.get("/trades", response_model=list[TradeOut])
def list_trades(
    account_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return OrderService(db).list_trades(account_id=account_id)
