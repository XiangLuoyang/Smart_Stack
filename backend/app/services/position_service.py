"""持仓服务:加权平均成本更新、清零。

A 股规则:
- 买入:新均价 = (旧持仓*旧成本 + 本次买入*本次价格) / 新总持仓
- 卖出:均价不变(实现盈亏在资金侧体现),数量减少;数量为 0 时清零
- 不支持融券,卖出不能超过现有持仓(由风控拦截)
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.position import Position

logger = logging.getLogger(__name__)


class PositionService:
    def __init__(self, db: Session):
        self.db = db

    def get(self, account_id: str, symbol: str) -> Optional[Position]:
        stmt = select(Position).where(
            Position.account_id == account_id,
            Position.symbol == symbol,
        )
        return self.db.scalars(stmt).first()

    def list_positions(self, account_id: str) -> list[Position]:
        stmt = select(Position).where(Position.account_id == account_id)
        return list(self.db.scalars(stmt))

    def apply_buy(self, account_id: str, symbol: str, qty: float, price: float) -> Position:
        """买入成交后更新持仓:加权平均成本。"""
        pos = self.get(account_id, symbol)
        if pos is None:
            pos = Position(account_id=account_id, symbol=symbol, qty=0.0, avg_cost=0.0)
            self.db.add(pos)

        new_qty = pos.qty + qty
        if new_qty <= 0:
            pos.qty = 0.0
            pos.avg_cost = 0.0
        else:
            pos.avg_cost = (pos.qty * pos.avg_cost + qty * price) / new_qty
            pos.qty = new_qty
        self.db.flush()
        return pos

    def apply_sell(self, account_id: str, symbol: str, qty: float, price: float) -> Position | None:
        """卖出成交后更新持仓:均价不变,数量减少,清零时返回 None。"""
        pos = self.get(account_id, symbol)
        if pos is None:
            logger.error(f"卖出无持仓 {account_id} {symbol}")
            return None

        pos.qty -= qty
        if pos.qty <= 1e-9:
            self.db.delete(pos)
            self.db.flush()
            return None
        self.db.flush()
        return pos

    def set_stop_loss(self, account_id: str, symbol: str, price: float | None) -> Position | None:
        pos = self.get(account_id, symbol)
        if pos:
            pos.stop_loss_price = price
            self.db.commit()
            self.db.refresh(pos)
        return pos

    def set_take_profit(self, account_id: str, symbol: str, price: float | None) -> Position | None:
        pos = self.get(account_id, symbol)
        if pos:
            pos.take_profit_price = price
            self.db.commit()
            self.db.refresh(pos)
        return pos
