"""订单预留服务:冻结现金或股份,成交消耗/取消释放。"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.order import Order
from app.models.order_reservation import (
    RESERVATION_ACTIVE,
    RESERVATION_CONSUMED,
    RESERVATION_RELEASED,
    OrderReservation,
)
from app.models.position import Position

logger = logging.getLogger(__name__)

DEFAULT_FEE_RATE = 0.005  # 0.5% worst-case fee estimate


class ReservationError(Exception):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(message or code)


class ReservationService:
    def __init__(self, db: Session):
        self.db = db

    def reserve_for_buy(self, order: Order, estimated_price: float) -> OrderReservation:
        account = self.db.get(Account, order.account_id)
        if account is None:
            raise ReservationError("ACCOUNT_NOT_FOUND")
        notional = estimated_price * order.qty
        fee_estimate = notional * DEFAULT_FEE_RATE
        total_reserve = notional + fee_estimate
        available = account.cash - account.reserved_cash
        if total_reserve > available:
            raise ReservationError(
                "INSUFFICIENT_CASH",
                f"need {total_reserve:.2f}, available {available:.2f}",
            )
        account.reserved_cash += total_reserve
        reservation = OrderReservation(
            order_id=order.id,
            account_id=account.id,
            cash_amount=total_reserve,
            state=RESERVATION_ACTIVE,
        )
        self.db.add(reservation)
        self.db.flush()
        return reservation

    def reserve_for_sell(self, order: Order, sellable_qty: int) -> OrderReservation:
        if order.qty > sellable_qty:
            raise ReservationError(
                "INSUFFICIENT_SHARES",
                f"sellable {sellable_qty}, requested {int(order.qty)}",
            )
        position = self.db.scalars(
            select(Position).where(
                Position.account_id == order.account_id,
                Position.symbol == order.symbol,
            )
        ).first()
        if position:
            position.reserved_qty += order.qty
        reservation = OrderReservation(
            order_id=order.id,
            account_id=order.account_id,
            qty=int(order.qty),
            state=RESERVATION_ACTIVE,
        )
        self.db.add(reservation)
        self.db.flush()
        return reservation

    def release(self, order_id: str) -> None:
        reservation = self.db.scalars(
            select(OrderReservation).where(
                OrderReservation.order_id == order_id,
                OrderReservation.state == RESERVATION_ACTIVE,
            )
        ).first()
        if reservation is None:
            return
        account = self.db.get(Account, reservation.account_id)
        if reservation.cash_amount and account:
            account.reserved_cash -= reservation.cash_amount
        if reservation.qty and account:
            position = self.db.scalars(
                select(Position).where(
                    Position.account_id == account.id,
                    Position.symbol == self._order_symbol(order_id),
                )
            ).first()
            if position:
                position.reserved_qty -= reservation.qty
        reservation.state = RESERVATION_RELEASED
        self.db.flush()

    def consume(self, order_id: str) -> None:
        reservation = self.db.scalars(
            select(OrderReservation).where(
                OrderReservation.order_id == order_id,
                OrderReservation.state == RESERVATION_ACTIVE,
            )
        ).first()
        if reservation is None:
            return
        account = self.db.get(Account, reservation.account_id)
        if reservation.cash_amount and account:
            account.reserved_cash -= reservation.cash_amount
        if reservation.qty and account:
            position = self.db.scalars(
                select(Position).where(
                    Position.account_id == account.id,
                    Position.symbol == self._order_symbol(order_id),
                )
            ).first()
            if position:
                position.reserved_qty -= reservation.qty
        reservation.state = RESERVATION_CONSUMED
        self.db.flush()

    def _order_symbol(self, order_id: str) -> str:
        order = self.db.get(Order, order_id)
        return order.symbol if order else ""