"""两步订单确认服务:preview -> confirm。

preview 创建 60 秒有效的预览(不产生订单);
confirm 验证预览有效性后原子地创建订单+预留+撮合。
"""
from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.ashare_rules import (
    InstrumentState,
    OrderIntent,
    validate_order_rules,
)
from app.engine.matching import MatchingEngine, Quote
from app.models.account import Account
from app.models.order import Order, ORDER_STATUS_FILLED, ORDER_STATUS_PENDING, ORDER_STATUS_REJECTED
from app.models.order_preview import PREVIEW_TTL_SECONDS, OrderPreview
from app.models.position import Position
from app.models.trade import Trade
from app.services.reservation_service import ReservationService
from app.services.settlement_service import SettlementService

logger = logging.getLogger(__name__)


class ConfirmationError(Exception):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(message or code)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class OrderConfirmationService:
    def __init__(self, db: Session, calendar=None):
        self.db = db
        self.calendar = calendar
        self.reservation_svc = ReservationService(db)
        self.settlement_svc = SettlementService(db, calendar)
        self.matching_engine = MatchingEngine()

    def preview(
        self,
        account_id: str,
        symbol: str,
        side: str,
        qty: int,
        order_type: str = "MARKET",
        price: float | None = None,
        research_case_id: str | None = None,
        decision_entry_id: str | None = None,
        quote: Quote | None = None,
        instrument_state: InstrumentState | None = None,
        sellable_qty: int = 0,
    ) -> OrderPreview:
        now = _utcnow()
        if instrument_state:
            decision = validate_order_rules(
                OrderIntent(symbol=symbol, side=side, qty=qty, price=price, order_type=order_type),
                instrument_state,
                now,
                sellable_qty=sellable_qty,
            )
            if not decision.allowed:
                raise ConfirmationError(decision.code, decision.message)

        quote_price = quote.price if quote else None
        quote_ts = quote.ts if quote else None
        est_price = price or quote_price or 0
        fee_estimate = est_price * qty * 0.005

        token = secrets.token_hex(16)
        preview = OrderPreview(
            account_id=account_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            qty=qty,
            price=price,
            research_case_id=research_case_id,
            decision_entry_id=decision_entry_id,
            quote_price=quote_price,
            quote_ts=quote_ts,
            fee_estimate=fee_estimate,
            confirmation_token=token,
            expires_at=now + timedelta(seconds=PREVIEW_TTL_SECONDS),
            confirmed=False,
        )
        self.db.add(preview)
        self.db.flush()
        return preview

    def confirm(
        self,
        preview_id: str,
        confirmation_token: str,
        idempotency_key: str,
        quote: Quote | None = None,
        instrument_state: InstrumentState | None = None,
        sellable_qty: int = 0,
    ) -> dict:
        now = _utcnow()

        existing = self.db.scalars(
            select(Order).where(Order.idempotency_key == idempotency_key)
        ).first()
        if existing:
            return {"order_id": existing.id, "status": existing.status, "idempotent": True}

        preview = self.db.get(OrderPreview, preview_id)
        if preview is None:
            raise ConfirmationError("PREVIEW_NOT_FOUND")
        if preview.confirmation_token != confirmation_token:
            raise ConfirmationError("INVALID_TOKEN")
        if preview.confirmed:
            raise ConfirmationError("ALREADY_CONFIRMED")
        if now > preview.expires_at:
            raise ConfirmationError("PREVIEW_EXPIRED")

        if instrument_state:
            decision = validate_order_rules(
                OrderIntent(
                    symbol=preview.symbol, side=preview.side,
                    qty=preview.qty, price=preview.price,
                    order_type=preview.order_type,
                ),
                instrument_state,
                now,
                sellable_qty=sellable_qty,
            )
            if not decision.allowed:
                raise ConfirmationError(decision.code, decision.message)

        order = Order(
            account_id=preview.account_id,
            symbol=preview.symbol,
            side=preview.side,
            order_type=preview.order_type,
            qty=preview.qty,
            price=preview.price,
            status=ORDER_STATUS_PENDING,
            research_case_id=preview.research_case_id,
            decision_entry_id=preview.decision_entry_id,
            idempotency_key=idempotency_key,
            confirmed_at=now,
        )
        self.db.add(order)
        self.db.flush()

        if preview.side == "BUY":
            est_price = preview.price or (quote.price if quote else 0)
            self.reservation_svc.reserve_for_buy(order, est_price)
        else:
            self.reservation_svc.reserve_for_sell(order, sellable_qty)

        match_quote = quote or (
            Quote(symbol=preview.symbol, price=preview.quote_price, ts=preview.quote_ts)
            if preview.quote_price else None
        )
        result = self.matching_engine.match(order, match_quote)

        if result.filled:
            order.status = ORDER_STATUS_FILLED
            order.filled_qty = result.fill_qty
            order.filled_price = result.fill_price
            order.filled_at = now
            trade = Trade(
                order_id=order.id,
                account_id=order.account_id,
                symbol=order.symbol,
                side=order.side,
                qty=result.fill_qty,
                price=result.fill_price,
                filled_at=now,
            )
            self.db.add(trade)
            self.db.flush()

            account = self.db.get(Account, order.account_id)
            if order.side == "BUY":
                cost = result.fill_price * result.fill_qty
                account.cash -= cost
                self.reservation_svc.consume(order.id)
                pos = self.db.scalars(
                    select(Position).where(
                        Position.account_id == account.id,
                        Position.symbol == order.symbol,
                    )
                ).first()
                if pos is None:
                    pos = Position(account_id=account.id, symbol=order.symbol, qty=0, avg_cost=0)
                    self.db.add(pos)
                    self.db.flush()
                total_cost = pos.avg_cost * pos.qty + cost
                pos.qty += result.fill_qty
                pos.avg_cost = total_cost / pos.qty if pos.qty > 0 else 0
                if self.calendar:
                    sellable_on = self.calendar.shift(now.date(), 1)
                else:
                    from datetime import timedelta as td
                    sellable_on = now.date() + td(days=1)
                self.settlement_svc.create_lot(
                    account.id, order.symbol, trade.id,
                    int(result.fill_qty), now.date(), sellable_on,
                )
            else:
                proceeds = result.fill_price * result.fill_qty
                account.cash += proceeds
                self.reservation_svc.consume(order.id)
                pos = self.db.scalars(
                    select(Position).where(
                        Position.account_id == account.id,
                        Position.symbol == order.symbol,
                    )
                ).first()
                if pos:
                    pos.qty -= result.fill_qty
                self.settlement_svc.consume_for_sell(
                    account.id, order.symbol, int(result.fill_qty), now.date()
                )
        else:
            self.reservation_svc.release(order.id)
            order.status = ORDER_STATUS_REJECTED
            order.reject_reason = result.reason

        preview.confirmed = True
        preview.result_json = json.dumps({"order_id": order.id, "status": order.status})
        self.db.flush()

        return {"order_id": order.id, "status": order.status, "idempotent": False}