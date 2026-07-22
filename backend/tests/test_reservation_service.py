"""预留服务测试。"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.models  # noqa: F401
from app.models.account import Account
from app.models.order import Order
from app.models.position import Position
from app.services.reservation_service import ReservationError, ReservationService


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
def buy_order(db, account):
    order = Order(account_id=account.id, symbol="000001", side="BUY", order_type="LIMIT", qty=100, price=10.0)
    db.add(order)
    db.flush()
    return order


class TestBuyReservation:
    def test_reserves_principal_and_fee(self, db, account, buy_order):
        svc = ReservationService(db)
        res = svc.reserve_for_buy(buy_order, estimated_price=10.0)
        assert res.cash_amount == pytest.approx(1000 * 1.005)
        assert account.reserved_cash == pytest.approx(1005.0)

    def test_insufficient_cash_rejected(self, db, buy_order):
        account = db.get(Account, buy_order.account_id)
        account.cash = 500.0
        svc = ReservationService(db)
        with pytest.raises(ReservationError) as exc_info:
            svc.reserve_for_buy(buy_order, estimated_price=10.0)
        assert exc_info.value.code == "INSUFFICIENT_CASH"

    def test_two_orders_cannot_overspend(self, db, account):
        account.cash = 1500.0
        o1 = Order(account_id=account.id, symbol="000001", side="BUY", order_type="LIMIT", qty=100, price=10.0)
        o2 = Order(account_id=account.id, symbol="600000", side="BUY", order_type="LIMIT", qty=100, price=10.0)
        db.add_all([o1, o2])
        db.flush()
        svc = ReservationService(db)
        svc.reserve_for_buy(o1, estimated_price=10.0)
        with pytest.raises(ReservationError) as exc_info:
            svc.reserve_for_buy(o2, estimated_price=10.0)
        assert exc_info.value.code == "INSUFFICIENT_CASH"


class TestReleaseConsume:
    def test_release_frees_cash(self, db, account, buy_order):
        svc = ReservationService(db)
        svc.reserve_for_buy(buy_order, estimated_price=10.0)
        assert account.reserved_cash > 0
        svc.release(buy_order.id)
        assert account.reserved_cash == pytest.approx(0.0)

    def test_consume_frees_reservation(self, db, account, buy_order):
        svc = ReservationService(db)
        svc.reserve_for_buy(buy_order, estimated_price=10.0)
        svc.consume(buy_order.id)
        assert account.reserved_cash == pytest.approx(0.0)

    def test_double_release_is_noop(self, db, account, buy_order):
        svc = ReservationService(db)
        svc.reserve_for_buy(buy_order, estimated_price=10.0)
        svc.release(buy_order.id)
        svc.release(buy_order.id)  # second release is no-op
        assert account.reserved_cash == pytest.approx(0.0)


class TestSellReservation:
    def test_sell_reserves_qty(self, db, account):
        pos = Position(account_id=account.id, symbol="000001", qty=500, reserved_qty=0)
        db.add(pos)
        order = Order(account_id=account.id, symbol="000001", side="SELL", order_type="MARKET", qty=200)
        db.add(order)
        db.flush()
        svc = ReservationService(db)
        res = svc.reserve_for_sell(order, sellable_qty=500)
        assert res.qty == 200
        assert pos.reserved_qty == 200

    def test_sell_insufficient_rejected(self, db, account):
        order = Order(account_id=account.id, symbol="000001", side="SELL", order_type="MARKET", qty=200)
        db.add(order)
        db.flush()
        svc = ReservationService(db)
        with pytest.raises(ReservationError) as exc_info:
            svc.reserve_for_sell(order, sellable_qty=100)
        assert exc_info.value.code == "INSUFFICIENT_SHARES"