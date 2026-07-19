"""订单服务:下单全链路编排。

流程:风控前置 → 撮合 → 费用 → 持仓/资金/成交 落库(单事务)。
市价单即时成交,限价单未触及则入 PENDING 队列,由调度器巡检。
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.fees import FeesCalculator
from app.engine.matching import MatchingEngine, MatchResult, Quote
from app.engine.risk import AccountSnapshot, RiskEngine
from app.models.account import Account
from app.models.order import (
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_FILLED,
    ORDER_STATUS_PENDING,
    ORDER_STATUS_REJECTED,
    ORDER_TYPE_LIMIT,
    ORDER_TYPE_MARKET,
    Order,
)
from app.models.trade import Trade
from app.services.account_service import AccountService
from app.services.position_service import PositionService

logger = logging.getLogger(__name__)


class PlaceOrderResult:
    """下单返回的统一结构,既给 API 用也给调度器用。"""

    def __init__(
        self,
        order: Order,
        accepted: bool,
        message: str = "",
        trade: Optional[Trade] = None,
    ):
        self.order = order
        self.accepted = accepted
        self.message = message
        self.trade = trade


class OrderService:
    def __init__(
        self,
        db: Session,
        matching_engine: MatchingEngine | None = None,
        risk_engine: RiskEngine | None = None,
        fees_calculator: FeesCalculator | None = None,
    ):
        self.db = db
        self.matching = matching_engine or MatchingEngine()
        self.risk = risk_engine or RiskEngine()
        self.fees = fees_calculator or FeesCalculator()
        self.account_svc = AccountService(db)
        self.position_svc = PositionService(db)

    # ---------------- 下单 ----------------

    def place(
        self,
        account_id: str,
        symbol: str,
        side: str,
        qty: float,
        order_type: str,
        price: Optional[float] = None,
        quote: Optional[Quote] = None,
    ) -> PlaceOrderResult:
        """下单入口。返回 PlaceOrderResult,不抛异常(失败时 accepted=False)。"""
        account = self.account_svc.get(account_id)
        if not account:
            return PlaceOrderResult(Order(), accepted=False, message="账户不存在")
        if account.status != "ACTIVE":
            return PlaceOrderResult(Order(), accepted=False, message=f"账户状态 {account.status},不可交易")

        if qty <= 0:
            return PlaceOrderResult(Order(), accepted=False, message="数量必须大于 0")
        if order_type == ORDER_TYPE_LIMIT and price is None:
            return PlaceOrderResult(Order(), accepted=False, message="限价单缺少价格")

        # 撮合参考价(限价单为保护,市价单必须有行情)
        ref_quote = quote
        if ref_quote is None and order_type == ORDER_TYPE_MARKET:
            return PlaceOrderResult(Order(), accepted=False, message="市价单缺少最新行情")
        ref_price = price if order_type == ORDER_TYPE_LIMIT else (ref_quote.price if ref_quote else None)
        if ref_price is None:
            return PlaceOrderResult(Order(), accepted=False, message="无法确定参考价")

        # 1) 风控前置
        rule = self.account_svc.get_risk_rule(account_id)
        if rule is None:
            return PlaceOrderResult(Order(), accepted=False, message="账户无风控规则")
        snapshot = self._build_snapshot(account_id, symbol, account.cash)
        check = self.risk.pre_trade_check(rule, snapshot, side, symbol, qty, ref_price)
        if not check.passed:
            order = Order(
                account_id=account_id, symbol=symbol, side=side, order_type=order_type,
                qty=qty, price=price, status=ORDER_STATUS_REJECTED,
                reject_reason=f"{check.reason_code}: {check.message}",
            )
            self.db.add(order)
            self.db.commit()
            return PlaceOrderResult(order, accepted=False, message=check.message)

        # 2) 建订单(默认 PENDING)
        order = Order(
            account_id=account_id, symbol=symbol, side=side, order_type=order_type,
            qty=qty, price=price, status=ORDER_STATUS_PENDING,
        )
        self.db.add(order)
        self.db.flush()

        # 3) 撮合(市价单即时;限价单需要 quote)
        result = self._try_fill(order, ref_quote)

        if result.filled:
            self._settle(order, result.fill_price, result.fill_qty)
            self.db.commit()
            self.db.refresh(order)
            trade = order.trades[-1] if order.trades else None
            return PlaceOrderResult(order, accepted=True, message="已成交", trade=trade)

        # 限价单未触及:留在 PENDING,等待调度器
        self.db.commit()
        self.db.refresh(order)
        return PlaceOrderResult(order, accepted=True, message="限价单挂单中,等待价格触及")

    def _try_fill(self, order: Order, quote: Optional[Quote]) -> MatchResult:
        if order.order_type == ORDER_TYPE_MARKET:
            if quote is None:
                return MatchResult(filled=False, reason="市价单缺少行情")
            return self.matching.match(order, quote)
        # LIMIT:有 quote 才尝试,没有则挂起
        if quote is None:
            return MatchResult.pending()
        return self.matching.match(order, quote)

    def _settle(self, order: Order, fill_price: float, fill_qty: float) -> None:
        """成交后:订单状态 + 成交流水 + 资金 + 持仓(单事务内)。"""
        now = datetime.now()
        order.status = ORDER_STATUS_FILLED
        order.filled_qty = fill_qty
        order.filled_price = fill_price
        order.filled_at = now

        fee = self.fees.calc(order.side, order.symbol, fill_price, fill_qty)
        delta = self.fees.cash_delta(order.side, order.symbol, fill_price, fill_qty)
        account = self.account_svc.get(order.account_id)
        account.cash = round(account.cash + delta, 4)

        # 持仓更新
        if order.side == "BUY":
            self.position_svc.apply_buy(order.account_id, order.symbol, fill_qty, fill_price)
        else:
            self.position_svc.apply_sell(order.account_id, order.symbol, fill_qty, fill_price)

        # 成交流水
        trade = Trade(
            order_id=order.id,
            account_id=order.account_id,
            symbol=order.symbol,
            side=order.side,
            qty=fill_qty,
            price=fill_price,
            commission=fee.commission,
            stamp_duty=fee.stamp_duty,
            transfer_fee=fee.transfer_fee,
            # total_cost 存带符号现金变化(买入负、卖出正),保留向后语义
            total_cost=delta,
            filled_at=now,
        )
        self.db.add(trade)

    def _build_snapshot(self, account_id: str, symbol: str, cash: float) -> AccountSnapshot:
        positions = self.position_svc.list_positions(account_id)
        total_market_value = sum(p.qty * p.avg_cost for p in positions)  # 用成本近似
        target = next((p for p in positions if p.symbol == symbol), None)
        today_count = self.account_svc.today_trade_count(account_id)
        return AccountSnapshot(
            cash=cash,
            total_market_value=total_market_value,
            target_holding_value=(target.qty * target.avg_cost) if target else 0.0,
            target_holding_qty=target.qty if target else 0.0,
            today_trade_count=today_count,
        )

    # ---------------- 撤单 ----------------

    def cancel(self, order_id: str) -> tuple[bool, str]:
        order = self.db.get(Order, order_id)
        if not order:
            return False, "订单不存在"
        if order.status != ORDER_STATUS_PENDING:
            return False, f"订单状态 {order.status},无法撤销"
        order.status = ORDER_STATUS_CANCELLED
        self.db.commit()
        return True, "已撤销"

    # ---------------- 查询 ----------------

    def list_orders(
        self, account_id: Optional[str] = None, status: Optional[str] = None
    ) -> list[Order]:
        stmt = select(Order).order_by(Order.created_at.desc())
        if account_id:
            stmt = stmt.where(Order.account_id == account_id)
        if status:
            stmt = stmt.where(Order.status == status)
        return list(self.db.scalars(stmt))

    def list_trades(self, account_id: Optional[str] = None) -> list[Trade]:
        stmt = select(Trade).order_by(Trade.filled_at.desc())
        if account_id:
            stmt = stmt.where(Trade.account_id == account_id)
        return list(self.db.scalars(stmt))

    # ---------------- 限价单巡检 ----------------

    def scan_pending_orders(self, quotes: dict[str, Quote]) -> int:
        """调度器调用:对所有 PENDING 限价单尝试撮合,返回本次成交数量。"""
        stmt = select(Order).where(Order.status == ORDER_STATUS_PENDING)
        filled_count = 0
        for order in self.db.scalars(stmt):
            q = quotes.get(order.symbol)
            if q is None:
                continue
            result = self.matching.match(order, q)
            if result.filled and result.fill_price and result.fill_qty:
                self._settle(order, result.fill_price, result.fill_qty)
                filled_count += 1
        if filled_count > 0:
            self.db.commit()
        return filled_count
