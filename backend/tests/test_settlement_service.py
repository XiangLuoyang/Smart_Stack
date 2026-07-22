"""T+1 结算批次测试。"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.models  # noqa: F401
from app.models.account import Account
from app.models.order import Order
from app.models.trade import Trade
from app.services.settlement_service import SettlementService
from datetime import datetime


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def account(db):
    acct = Account(name="test", cash=100000.0)
    db.add(acct)
    db.flush()
    return acct


@pytest.fixture
def trade(db, account):
    order = Order(account_id=account.id, symbol="000001", side="BUY", order_type="MARKET", qty=100)
    db.add(order)
    db.flush()
    t = Trade(order_id=order.id, account_id=account.id, symbol="000001", side="BUY", qty=100, price=10.0, filled_at=datetime(2026, 7, 21, 10, 0))
    db.add(t)
    db.flush()
    return t


class TestSettlementLots:
    def test_today_buy_not_sellable(self, db, account, trade):
        svc = SettlementService(db)
        svc.create_lot(account.id, "000001", trade.id, 100, date(2026, 7, 21), date(2026, 7, 22))
        assert svc.sellable_qty(account.id, "000001", date(2026, 7, 21)) == 0
        assert svc.sellable_qty(account.id, "000001", date(2026, 7, 22)) == 100

    def test_fifo_consume(self, db, account, trade):
        svc = SettlementService(db)
        svc.create_lot(account.id, "000001", trade.id, 100, date(2026, 7, 20), date(2026, 7, 21))
        svc.create_lot(account.id, "000001", trade.id, 200, date(2026, 7, 21), date(2026, 7, 22))
        consumed = svc.consume_for_sell(account.id, "000001", 150, date(2026, 7, 22))
        assert len(consumed) == 2
        assert consumed[0].remaining_qty == 0
        assert consumed[1].remaining_qty == 150
        assert svc.sellable_qty(account.id, "000001", date(2026, 7, 22)) == 150

    def test_consume_insufficient_raises(self, db, account, trade):
        svc = SettlementService(db)
        svc.create_lot(account.id, "000001", trade.id, 100, date(2026, 7, 21), date(2026, 7, 22))
        with pytest.raises(ValueError, match="insufficient lots"):
            svc.consume_for_sell(account.id, "000001", 200, date(2026, 7, 22))