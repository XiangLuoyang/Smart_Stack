"""Phase 3 T1: 操作账本原语 schema 测试。"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.models  # noqa: F401
from app.models.account import Account
from app.models.order import Order
from app.models.order_reservation import OrderReservation
from app.models.position import Position
from app.models.settlement_lot import SettlementLot
from app.models.trade import Trade


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_account_has_reserved_cash(db_session):
    acct = Account(name="test", cash=100000.0, reserved_cash=5000.0)
    db_session.add(acct)
    db_session.commit()
    assert acct.reserved_cash == 5000.0


def test_position_has_reserved_qty(db_session):
    acct = Account(name="test", cash=100000.0)
    db_session.add(acct)
    db_session.flush()
    pos = Position(account_id=acct.id, symbol="000001", qty=1000, reserved_qty=200)
    db_session.add(pos)
    db_session.commit()
    assert pos.reserved_qty == 200


def test_order_has_research_linkage(db_session):
    acct = Account(name="test", cash=100000.0)
    db_session.add(acct)
    db_session.flush()
    order = Order(
        account_id=acct.id,
        symbol="000001",
        side="BUY",
        order_type="LIMIT",
        qty=100,
        price=10.0,
        idempotency_key="test-key-1",
    )
    db_session.add(order)
    db_session.commit()
    assert order.idempotency_key == "test-key-1"
    assert order.research_case_id is None
    assert order.confirmed_at is None


def test_idempotency_key_unique(db_session):
    acct = Account(name="test", cash=100000.0)
    db_session.add(acct)
    db_session.flush()
    o1 = Order(account_id=acct.id, symbol="000001", side="BUY", order_type="LIMIT", qty=100, price=10.0, idempotency_key="dup-key")
    o2 = Order(account_id=acct.id, symbol="600000", side="BUY", order_type="LIMIT", qty=100, price=8.0, idempotency_key="dup-key")
    db_session.add(o1)
    db_session.commit()
    db_session.add(o2)
    with pytest.raises(Exception):
        db_session.commit()
    db_session.rollback()


def test_settlement_lot(db_session):
    acct = Account(name="test", cash=100000.0)
    db_session.add(acct)
    db_session.flush()
    order = Order(account_id=acct.id, symbol="000001", side="BUY", order_type="MARKET", qty=100)
    db_session.add(order)
    db_session.flush()
    from datetime import datetime
    trade = Trade(
        order_id=order.id, account_id=acct.id, symbol="000001",
        side="BUY", qty=100, price=10.0, filled_at=datetime.now(),
    )
    db_session.add(trade)
    db_session.flush()
    lot = SettlementLot(
        account_id=acct.id, symbol="000001", trade_id=trade.id,
        acquired_date=date(2026, 7, 21), sellable_on=date(2026, 7, 22),
        total_qty=100, remaining_qty=100,
    )
    db_session.add(lot)
    db_session.commit()
    assert lot.remaining_qty == 100
    assert lot.sellable_on == date(2026, 7, 22)


def test_order_reservation(db_session):
    acct = Account(name="test", cash=100000.0)
    db_session.add(acct)
    db_session.flush()
    order = Order(account_id=acct.id, symbol="000001", side="BUY", order_type="LIMIT", qty=100, price=10.0)
    db_session.add(order)
    db_session.flush()
    res = OrderReservation(
        order_id=order.id, account_id=acct.id,
        cash_amount=1005.0, state="ACTIVE",
    )
    db_session.add(res)
    db_session.commit()
    assert res.cash_amount == 1005.0
    assert res.state == "ACTIVE"