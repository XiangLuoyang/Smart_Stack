"""并发安全测试:两个确认不能超支。"""
from __future__ import annotations

import threading
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.models  # noqa: F401
from app.engine.matching import Quote
from app.models.account import Account
from app.services.order_confirmation_service import OrderConfirmationService


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture
def file_engine(tmp_path):
    url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 5})
    Base.metadata.create_all(engine)
    return engine


def test_two_confirms_cannot_overspend(file_engine):
    """两个线程同时确认买入,只有一个能成功(资金仅够一笔)。"""
    Session = sessionmaker(bind=file_engine, autoflush=False, autocommit=False)

    setup_session = Session()
    account = Account(name="test", cash=1500.0)
    setup_session.add(account)
    setup_session.commit()
    account_id = account.id
    setup_session.close()

    quote = Quote(symbol="000001", price=10.0, ts=_utcnow())

    preview_ids = []
    tokens = []
    for i in range(2):
        s = Session()
        svc = OrderConfirmationService(s)
        p = svc.preview(account_id, "000001", "BUY", 100, order_type="LIMIT", price=10.0, quote=quote)
        s.commit()
        preview_ids.append(p.id)
        tokens.append(p.confirmation_token)
        s.close()

    results = [None, None]
    errors = [None, None]

    def confirm(idx):
        s = Session()
        try:
            svc = OrderConfirmationService(s)
            r = svc.confirm(preview_ids[idx], tokens[idx], f"key-{idx}", quote=quote)
            s.commit()
            results[idx] = r
        except Exception as e:
            s.rollback()
            errors[idx] = e
        finally:
            s.close()

    t1 = threading.Thread(target=confirm, args=(0,))
    t2 = threading.Thread(target=confirm, args=(1,))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    success_count = sum(1 for r in results if r and r.get("status") == "FILLED")
    assert success_count <= 1, f"Both orders filled! results={results}"

    verify_session = Session()
    acct = verify_session.get(Account, account_id)
    assert acct.cash >= 0, f"Cash went negative: {acct.cash}"
    assert acct.reserved_cash >= 0, f"Reserved cash negative: {acct.reserved_cash}"
    verify_session.close()