"""复盘队列 API 测试。

验证:
- 复盘笔记不修改自动结算结果;
- 无效标签 -> 422;
- 无关联案例 -> 404;
- 预测不存在 -> 404。
"""
from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.models  # noqa: F401
from app.models.forecast import ModelVersion, PredictionSnapshot, ReviewResult
from app.models.research import ResearchCase


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
def settled_review(db_session):
    model = ModelVersion(name="test-model", version="1.0.0")
    db_session.add(model)
    db_session.flush()

    pred = PredictionSnapshot(
        business_date=date(2026, 7, 1),
        symbol="000001",
        model_version_id=model.id,
        horizon_days=10,
        p_up=0.5, p_flat=0.2, p_down=0.3,
        median_return=0.02,
        lower_return=-0.01,
        upper_return=0.05,
        expected_excess_return=0.015,
        expected_mfe=0.03,
        expected_mae=-0.01,
        state="SETTLED",
    )
    db_session.add(pred)
    db_session.flush()

    review = ReviewResult(
        prediction_snapshot_id=pred.id,
        actual_return=0.018,
        benchmark_excess=0.005,
        signed_error=-0.002,
        interval_coverage=True,
        mfe=0.025,
        mae=-0.005,
        direction_correct=True,
        state="SETTLED",
        settled_at=datetime(2026, 7, 15, 16, 0),
    )
    db_session.add(review)

    case = ResearchCase(
        symbol="000001",
        prediction_snapshot_id=pred.id,
        status="ACTIVE",
        initial_direction="BULLISH",
        thesis="test thesis",
        expected_return_lower=0.01,
        expected_return_upper=0.05,
        counterargument="test",
        invalidation_condition="test",
        planned_entry=10.0,
        target_price=10.5,
        stop_price=9.5,
        confidence=3,
        frozen_analysis_json="{}",
    )
    db_session.add(case)
    db_session.commit()
    return pred


class TestReviewNotes:
    def test_review_note_does_not_modify_market_result(self, client, settled_review):
        before = client.get(f"/api/reviews/{settled_review.id}").json()
        response = client.post(
            f"/api/reviews/{settled_review.id}/notes",
            json={
                "attribution": "direction correct but entry too early",
                "error_tags": ["EARLY_ENTRY"],
                "discipline_followed": False,
            },
        )
        assert response.status_code == 201
        after = client.get(f"/api/reviews/{settled_review.id}").json()
        assert after["review"]["actual_return"] == before["review"]["actual_return"]
        assert len(after["notes"]) == 1

    def test_invalid_tag_gives_422(self, client, settled_review):
        resp = client.post(
            f"/api/reviews/{settled_review.id}/notes",
            json={"attribution": "test", "error_tags": ["INVALID_TAG"]},
        )
        assert resp.status_code == 422

    def test_no_linked_case_gives_404(self, client, db_session):
        model = ModelVersion(name="m2", version="1.0.0")
        db_session.add(model)
        db_session.flush()
        pred = PredictionSnapshot(
            business_date=date(2026, 7, 1),
            symbol="600000",
            model_version_id=model.id,
            horizon_days=10,
            p_up=0.5, p_flat=0.2, p_down=0.3,
            median_return=0.01,
            lower_return=-0.01,
            upper_return=0.03,
            expected_excess_return=0.01,
            expected_mfe=0.02,
            expected_mae=-0.01,
            state="SETTLED",
        )
        db_session.add(pred)
        db_session.commit()
        resp = client.post(
            f"/api/reviews/{pred.id}/notes",
            json={"attribution": "test", "error_tags": []},
        )
        assert resp.status_code == 404

    def test_prediction_not_found_gives_404(self, client):
        resp = client.get("/api/reviews/nonexistent-id")
        assert resp.status_code == 404

    def test_get_review_detail(self, client, settled_review):
        resp = client.get(f"/api/reviews/{settled_review.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "000001"
        assert data["review"]["actual_return"] == 0.018
        assert data["review"]["direction_correct"] is True
        assert len(data["cases"]) == 1