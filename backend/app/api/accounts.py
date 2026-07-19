"""账户 + 持仓 + 成交查询路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_market_service_with_db
from app.schemas.account import AccountCreate, AccountOut, AccountOverview
from app.schemas.order import TradeOut
from app.services.account_service import AccountService
from app.services.market_service import MarketService
from app.services.position_service import PositionService

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    account = AccountService(db).create_account(payload.name, payload.initial_cash)
    return account


@router.get("", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    return AccountService(db).list_accounts()


@router.get("/{account_id}", response_model=AccountOverview)
def get_account(
    account_id: str,
    db: Session = Depends(get_db),
    market: MarketService = Depends(get_market_service_with_db),
):
    overview = AccountService(db).overview(account_id, market)
    if overview is None:
        raise HTTPException(404, "账户不存在")
    return overview


@router.get("/{account_id}/trades", response_model=list[TradeOut])
def list_account_trades(account_id: str, db: Session = Depends(get_db)):
    svc = AccountService(db)
    if not svc.get(account_id):
        raise HTTPException(404, "账户不存在")
    from app.services.order_service import OrderService
    return OrderService(db).list_trades(account_id)


@router.get("/{account_id}/positions")
def list_account_positions(account_id: str, db: Session = Depends(get_db)):
    svc = AccountService(db)
    if not svc.get(account_id):
        raise HTTPException(404, "账户不存在")
    positions = PositionService(db).list_positions(account_id)
    return [
        {
            "symbol": p.symbol,
            "qty": p.qty,
            "avg_cost": p.avg_cost,
            "stop_loss_price": p.stop_loss_price,
            "take_profit_price": p.take_profit_price,
        }
        for p in positions
    ]
