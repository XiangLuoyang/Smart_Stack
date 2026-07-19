"""风控规则路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.risk_rule import RiskRuleOut, RiskRuleUpdate
from app.services.account_service import AccountService

router = APIRouter(prefix="/api/risk-rules", tags=["risk_rules"])


@router.get("/{account_id}", response_model=RiskRuleOut)
def get_rule(account_id: str, db: Session = Depends(get_db)):
    rule = AccountService(db).get_risk_rule(account_id)
    if not rule:
        raise HTTPException(404, "账户无风控规则")
    return rule


@router.put("/{account_id}", response_model=RiskRuleOut)
def update_rule(
    account_id: str,
    payload: RiskRuleUpdate,
    db: Session = Depends(get_db),
):
    rule = AccountService(db).update_risk_rule(
        account_id,
        max_position_pct=payload.max_position_pct,
        max_single_pct=payload.max_single_pct,
        stop_loss_pct=payload.stop_loss_pct,
        take_profit_pct=payload.take_profit_pct,
        max_daily_trades=payload.max_daily_trades,
    )
    if not rule:
        raise HTTPException(404, "账户无风控规则")
    return rule
