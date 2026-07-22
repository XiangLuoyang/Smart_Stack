"""T+1 结算批次服务:追踪可卖性,FIFO 消耗。"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.settlement_lot import SettlementLot

logger = logging.getLogger(__name__)


class SettlementService:
    def __init__(self, db: Session, calendar=None):
        self.db = db
        self.calendar = calendar

    def create_lot(
        self,
        account_id: str,
        symbol: str,
        trade_id: str,
        qty: int,
        acquired_date: date,
        sellable_on: date,
    ) -> SettlementLot:
        lot = SettlementLot(
            account_id=account_id,
            symbol=symbol,
            trade_id=trade_id,
            acquired_date=acquired_date,
            sellable_on=sellable_on,
            total_qty=qty,
            remaining_qty=qty,
        )
        self.db.add(lot)
        self.db.flush()
        return lot

    def sellable_qty(self, account_id: str, symbol: str, on_date: date) -> int:
        lots = self.db.scalars(
            select(SettlementLot).where(
                SettlementLot.account_id == account_id,
                SettlementLot.symbol == symbol,
                SettlementLot.sellable_on <= on_date,
                SettlementLot.remaining_qty > 0,
            )
        ).all()
        return sum(lot.remaining_qty for lot in lots)

    def consume_for_sell(
        self, account_id: str, symbol: str, qty: int, on_date: date
    ) -> list[SettlementLot]:
        """FIFO 消耗最老的可卖批次,返回被消耗的批次列表。"""
        lots = list(
            self.db.scalars(
                select(SettlementLot)
                .where(
                    SettlementLot.account_id == account_id,
                    SettlementLot.symbol == symbol,
                    SettlementLot.sellable_on <= on_date,
                    SettlementLot.remaining_qty > 0,
                )
                .order_by(SettlementLot.sellable_on, SettlementLot.acquired_date)
            ).all()
        )
        remaining = qty
        consumed: list[SettlementLot] = []
        for lot in lots:
            if remaining <= 0:
                break
            take = min(lot.remaining_qty, remaining)
            lot.remaining_qty -= take
            remaining -= take
            consumed.append(lot)
        if remaining > 0:
            raise ValueError(f"insufficient lots: still need {remaining} shares")
        return consumed