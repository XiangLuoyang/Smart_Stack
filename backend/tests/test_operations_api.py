"""操作 API 测试:preview/confirm 两步流程。"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.models  # noqa: F401
from app.models.account import Account


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(db_session):
    from fastapi.testclient import TestClient
    from app.api.deps import get_db
    from app.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def account(db_session):
    acct = Account(name="test", cash=100000.0)
    db_session.add(acct)
    db_session.commit()
    return acct


class TestOperationsAPI:
    def test_preview_then_confirm(self, client, account):
        preview = client.post("/api/orders/preview", json={
            "account_id": account.id,
            "symbol": "000001",
            "side": "BUY",
            "qty": 100,
            "order_type": "LIMIT",
            "price": 10.0,
        })
        assert preview.status_code == 200
        data = preview.json()
        assert data["confirmation_token"]
        assert data["fee_estimate"] > 0

        confirm = client.post("/api/orders/confirm", json={
            "preview_id": data["id"],
            "confirmation_token": data["confirmation_token"],
            "idempotency_key": "test-key-1",
        })
        assert confirm.status_code == 201
        assert confirm.json()["status"] == "FILLED"

    def test_confirm_idempotent(self, client, account):
        preview = client.post("/api/orders/preview", json={
            "account_id": account.id, "symbol": "000001",
            "side": "BUY", "qty": 100, "price": 10.0, "order_type": "LIMIT",
        }).json()
        payload = {
            "preview_id": preview["id"],
            "confirmation_token": preview["confirmation_token"],
            "idempotency_key": "idem-1",
        }
        first = client.post("/api/orders/confirm", json=payload)
        second = client.post("/api/orders/confirm", json=payload)
        assert first.json()["order_id"] == second.json()["order_id"]

    def test_preview_not_found(self, client):
        resp = client.post("/api/orders/confirm", json={
            "preview_id": "nonexistent",
            "confirmation_token": "x",
            "idempotency_key": "y",
        })
        assert resp.status_code == 404