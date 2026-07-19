"""账户服务:建账户、查概览、浮动盈亏。"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.risk_rule import RiskRule

logger = logging.getLogger(__name__)


class AccountService:
    def __init__(self, db: Session):
        self.db = db

    def create_account(self, name: str, initial_cash: float = 1_000_000.0) -> Account:
        """创建虚拟账户,同时初始化默认风控规则。"""
        account = Account(name=name, cash=float(initial_cash), status="ACTIVE")
        self.db.add(account)
        self.db.flush()  # 拿到 id

        # 默认风控规则(用户后续可改)
        rule = RiskRule(account_id=account.id)
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(account)
        logger.info(f"创建账户 {account.id} 名 '{name}' 初始资金 {initial_cash}")
        return account

    def get(self, account_id: str) -> Account | None:
        return self.db.get(Account, account_id)

    def list_accounts(self) -> list[Account]:
        return list(self.db.scalars(select(Account).order_by(Account.created_at.desc())))

    def overview(self, account_id: str, market_service: "MarketService | None" = None) -> dict | None:
        """账户概览:现金 + 持仓 + 浮动盈亏。"""
        account = self.get(account_id)
        if not account:
            return None

        positions_data = []
        total_market_value = 0.0
        total_cost = 0.0
        for pos in account.positions:
            last_price = None
            if market_service:
                q = market_service.get_quote(pos.symbol)
                if q:
                    last_price = q.price
            last_price = last_price if last_price is not None else pos.avg_cost
            market_value = pos.qty * last_price
            cost = pos.qty * pos.avg_cost
            profit = market_value - cost
            total_market_value += market_value
            total_cost += cost
            positions_data.append({
                "symbol": pos.symbol,
                "qty": pos.qty,
                "avg_cost": pos.avg_cost,
                "last_price": last_price,
                "market_value": market_value,
                "profit": profit,
                "profit_pct": (profit / cost) if cost > 0 else 0.0,
                "stop_loss_price": pos.stop_loss_price,
                "take_profit_price": pos.take_profit_price,
            })

        total_assets = account.cash + total_market_value
        return {
            "account_id": account.id,
            "name": account.name,
            "cash": account.cash,
            "status": account.status,
            "positions": positions_data,
            "total_market_value": total_market_value,
            "total_cost": total_cost,
            "total_assets": total_assets,
            "floating_profit": total_market_value - total_cost,
            # 浮动盈亏率:相对初始投入的近似(现金+市值-成本)/成本
            "floating_profit_pct": (
                (total_market_value - total_cost) / total_cost if total_cost > 0 else 0.0
            ),
            "updated_at": account.updated_at,
        }

    def get_risk_rule(self, account_id: str) -> RiskRule | None:
        account = self.get(account_id)
        return account.risk_rule if account else None

    def update_risk_rule(self, account_id: str, **fields) -> RiskRule | None:
        rule = self.get_risk_rule(account_id)
        if not rule:
            return None
        for k, v in fields.items():
            if hasattr(rule, k) and v is not None:
                setattr(rule, k, v)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def today_trade_count(self, account_id: str) -> int:
        """今日该账户成交笔数(用于日内交易次数风控)。"""
        from app.models.trade import Trade
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = select(Trade).where(
            Trade.account_id == account_id,
            Trade.filled_at >= today_start,
        )
        return len(list(self.db.scalars(stmt)))
