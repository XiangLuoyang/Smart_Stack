"""研究闭环 REST API 测试。

验证:
- 案例创建 201,append-only(无 PATCH/DELETE);
- 证据/决策追加 201;
- 关闭后追加 -> 409;
- 不存在 -> 404;
- 单股研究视图 GET;
- 列表过滤。
"""
from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.models  # noqa: F401
from app.models.forecast import ModelVersion, PredictionSnapshot


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
def prediction(db_session):
    model = ModelVersion(name="historical-10d-baseline", version="1.0.0")
    db_session.add(model)
    db_session.flush()
    pred = PredictionSnapshot(
        business_date=date(2026, 7, 21),
        symbol="000001",
        model_version_id=model.id,
        horizon_days=10,
        p_up=0.45,
        p_flat=0.20,
        p_down=0.35,
        median_return=0.012,
        lower_return=-0.02,
        upper_return=0.05,
        expected_excess_return=0.03,
        expected_mfe=0.04,
        expected_mae=-0.015,
        state="PENDING",
    )
    db_session.add(pred)
    db_session.commit()
    return pred


def _case_payload(prediction_id: str) -> dict:
    return {
        "prediction_snapshot_id": prediction_id,
        "direction": "BULLISH",
        "thesis": "demand improvement",
        "expected_return_lower": 0.03,
        "expected_return_upper": 0.12,
        "counterargument": "priced in",
        "invalidation_condition": "break 20d low",
        "planned_entry": 10.0,
        "target_price": 11.2,
        "stop_price": 9.4,
        "confidence": 4,
    }


class TestCaseAPI:
    def test_create_case_returns_201(self, client, prediction):
        resp = client.post("/api/research/cases", json=_case_payload(prediction.id))
        assert resp.status_code == 201
        data = resp.json()
        assert data["symbol"] == "000001"
        assert data["status"] == "ACTIVE"
        assert data["initial_direction"] == "BULLISH"

    def test_case_api_is_append_only(self, client, prediction):
        created = client.post("/api/research/cases", json=_case_payload(prediction.id))
        case_id = created.json()["id"]
        resp = client.patch(f"/api/research/cases/{case_id}", json={"thesis": "rewrite"})
        assert resp.status_code == 405

    def test_delete_not_allowed(self, client, prediction):
        created = client.post("/api/research/cases", json=_case_payload(prediction.id))
        case_id = created.json()["id"]
        resp = client.delete(f"/api/research/cases/{case_id}")
        assert resp.status_code == 405

    def test_append_evidence(self, client, prediction):
        created = client.post("/api/research/cases", json=_case_payload(prediction.id))
        case_id = created.json()["id"]
        resp = client.post(
            f"/api/research/cases/{case_id}/evidence",
            json={
                "stance": "OPPOSE",
                "category": "VALUATION",
                "content": "valuation at 90th percentile",
                "source_label": "personal",
                "observed_date": "2026-07-22",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["stance"] == "OPPOSE"

    def test_append_decision(self, client, prediction):
        created = client.post("/api/research/cases", json=_case_payload(prediction.id))
        case_id = created.json()["id"]
        resp = client.post(
            f"/api/research/cases/{case_id}/decisions",
            json={
                "direction": "NEUTRAL",
                "action": "NO_ACTION",
                "rationale": "thesis weakened",
                "confidence": 2,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["direction"] == "NEUTRAL"

    def test_close_case_then_append_gives_409(self, client, prediction):
        created = client.post("/api/research/cases", json=_case_payload(prediction.id))
        case_id = created.json()["id"]
        close_resp = client.post(f"/api/research/cases/{case_id}/close")
        assert close_resp.status_code == 200
        assert close_resp.json()["status"] == "CLOSED"

        resp = client.post(
            f"/api/research/cases/{case_id}/evidence",
            json={
                "stance": "SUPPORT",
                "category": "EARNINGS",
                "content": "late evidence",
                "observed_date": "2026-07-22",
            },
        )
        assert resp.status_code == 409

    def test_not_found_gives_404(self, client):
        resp = client.get("/api/research/cases/nonexistent-id")
        assert resp.status_code == 404

    def test_create_with_bad_prediction_gives_404(self, client):
        payload = _case_payload("nonexistent-pred-id")
        resp = client.post("/api/research/cases", json=payload)
        assert resp.status_code == 404

    def test_list_cases_filter_by_symbol(self, client, prediction):
        client.post("/api/research/cases", json=_case_payload(prediction.id))
        resp = client.get("/api/research/cases", params={"symbol": "000001"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        resp2 = client.get("/api/research/cases", params={"symbol": "999999"})
        assert len(resp2.json()) == 0

    def test_get_case_includes_events(self, client, prediction):
        created = client.post("/api/research/cases", json=_case_payload(prediction.id))
        case_id = created.json()["id"]
        client.post(
            f"/api/research/cases/{case_id}/evidence",
            json={
                "stance": "SUPPORT",
                "category": "EARNINGS",
                "content": "earnings upgrade",
                "observed_date": "2026-07-22",
            },
        )
        resp = client.get(f"/api/research/cases/{case_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["evidence_entries"]) == 1
        assert len(data["decision_entries"]) == 1  # initial decision


class TestStockResearchEndpoint:
    def test_get_stock_research(self, client, prediction):
        resp = client.get("/api/research/stocks/000001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "000001"
        assert "forecast" in data
        assert "technical" in data
        assert "llm" in data