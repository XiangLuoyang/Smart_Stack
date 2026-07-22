"""单账户引导测试。"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.models  # noqa: F401
from app.models.account import Account
from app.services.bootstrap_service import ensure_single_account


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_creates_account_when_empty(db):
    acct = ensure_single_account(db)
    assert acct.name == "个人模拟账户"
    assert acct.cash == 1_000_000.0


def test_returns_existing_account(db):
    existing = Account(name="existing", cash=50000.0)
    db.add(existing)
    db.commit()
    acct = ensure_single_account(db)
    assert acct.id == existing.id
    assert acct.cash == 50000.0


def test_does_not_duplicate(db):
    ensure_single_account(db)
    ensure_single_account(db)
    from sqlalchemy import func, select
    count = db.scalar(select(func.count(Account.id)))
    assert count == 1