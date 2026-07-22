"""Phase 4 验收:指标计算 -> 聚合 -> 评估 -> 晋升门控。"""
from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.models  # noqa: F401
from app.engine.performance_metrics import direction_accuracy, model_metrics
from app.models.forecast import ModelVersion, PredictionSnapshot, ReviewResult
from app.models.performance import MetricBatch, ModelEvaluationRun, ModelPromotionDecision, PerformanceMetric
from app.services.model_evaluation_service import ModelEvaluationService
from app.services.performance_service import PerformanceService


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_performance_e2e(db):
    """完整性能闭环:预测 -> 结算 -> 指标计算 -> 评估 -> 晋升。"""
    model = ModelVersion(name="baseline", version="1.0.0")
    db.add(model)
    db.flush()

    for i in range(5):
        pred = PredictionSnapshot(
            business_date=date(2026, 7, 1 + i), symbol=f"00000{i}",
            model_version_id=model.id, horizon_days=10,
            p_up=0.5, p_flat=0.2, p_down=0.3,
            median_return=0.02, lower_return=-0.01, upper_return=0.05,
            expected_excess_return=0.015, expected_mfe=0.03, expected_mae=-0.01,
            state="SETTLED",
        )
        db.add(pred)
        db.flush()
        review = ReviewResult(
            prediction_snapshot_id=pred.id,
            actual_return=0.015 if i % 2 == 0 else -0.005,
            direction_correct=i % 2 == 0,
            interval_coverage=True,
            mfe=0.02, mae=-0.005,
            state="SETTLED",
        )
        db.add(review)
    db.flush()

    svc = PerformanceService(db)
    batch = svc.compute_model_metrics(model.id, date(2026, 7, 10))
    assert batch.status == "SUCCESS"
    assert batch.source_row_count == 5

    metrics = db.query(PerformanceMetric).filter_by(batch_id=batch.id).all()
    assert len(metrics) >= 3
    da_metric = next(m for m in metrics if m.metric_name == "direction_accuracy")
    assert da_metric.value is not None
    assert da_metric.sample_count == 5

    eval_svc = ModelEvaluationService(db)
    candidate = ModelVersion(name="challenger", version="2.0.0")
    db.add(candidate)
    db.flush()

    run = eval_svc.create_evaluation(candidate.id, model.id, {"direction_accuracy": 0.6, "mae": 0.03})
    assert run.status == "COMPLETED"

    decision = eval_svc.evaluate_promotion(
        run.id,
        {"direction_accuracy": 0.6, "mae": 0.03, "sample_count": 50},
    )
    assert decision.approved is True

    bad_decision = eval_svc.evaluate_promotion(
        run.id,
        {"direction_accuracy": 0.3, "mae": 0.08, "sample_count": 10},
    )
    assert bad_decision.approved is False