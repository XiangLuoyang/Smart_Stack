"""两步订单确认测试。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.models  # noqa: F401
from app.engine.matching import Quote
from app.models.account import Account
from app.models.order import Order
from app.services.order_confirmation_service import ConfirmationError, OrderConfirmationService


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
def svc(db):
    return OrderConfirmationService(db)


@pytest.fixture
def quote():
    return Quote(symbol="000001", price=10.0, ts=_utcnow())


class TestPreview:
    def test_preview_does_not_create_order(self, db, svc, account, quote):
        preview = svc.preview(account.id, "000001", "BUY", 100, quote=quote)
        assert preview.confirmation_token
        assert db.scalar(select(func.count(Order.id))) == 0

    def test_preview_has_expiry(self, svc, account, quote):
        preview = svc.preview(account.id, "000001", "BUY", 100, quote=quote)
        assert preview.expires_at > _utcnow()


class TestConfirm:
    def test_confirm_creates_order(self, db, svc, account, quote):
        preview = svc.preview(account.id, "000001", "BUY", 100, quote=quote)
        result = svc.confirm(preview.id, preview.confirmation_token, "key-1", quote=quote)
        assert result["status"] == "FILLED"
        assert db.scalar(select(func.count(Order.id))) == 1

    def test_confirm_is_idempotent(self, db, svc, account, quote):
        preview = svc.preview(account.id, "000001", "BUY", 100, quote=quote)
        first = svc.confirm(preview.id, preview.confirmation_token, "key-1", quote=quote)
        second = svc.confirm(preview.id, preview.confirmation_token, "key-1", quote=quote)
        assert second["order_id"] == first["order_id"]
        assert second["idempotent"] is True

    def test_expired_preview_cannot_confirm(self, db, svc, account, quote):
        preview = svc.preview(account.id, "000001", "BUY", 100, quote=quote)
        preview.expires_at = _utcnow() - timedelta(seconds=1)
        db.flush()
        with pytest.raises(ConfirmationError) as exc_info:
            svc.confirm(preview.id, preview.confirmation_token, "key-2", quote=quote)
        assert exc_info.value.code == "PREVIEW_EXPIRED"

    def test_invalid_token_rejected(self, db, svc, account, quote):
        preview = svc.preview(account.id, "000001", "BUY", 100, quote=quote)
        with pytest.raises(ConfirmationError) as exc_info:
            svc.confirm(preview.id, "wrong-token", "key-3", quote=quote)
        assert exc_info.value.code == "INVALID_TOKEN"

    def test_buy_deducts_cash(self, db, svc, account, quote):
        preview = svc.preview(account.id, "000001", "BUY", 100, quote=quote)
        svc.confirm(preview.id, preview.confirmation_token, "key-4", quote=quote)
        assert account.cash == pytest.approx(100000.0 - 1000.0)

    def test_confirm_updates_cash_and_position(self, db, svc, account, quote):
        from app.models.position import Position
        preview = svc.preview(account.id, "000001", "BUY", 100, quote=quote)
        svc.confirm(preview.id, preview.confirmation_token, "key-5", quote=quote)
        pos = db.scalars(select(Position).where(Position.symbol == "000001")).first()
        assert pos is not None
        assert pos.qty == 100
        assert pos.avg_cost == pytest.approx(10.0)