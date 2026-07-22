"""性能聚合服务:计算并持久化各维度指标。

维度:MODEL(模型预测)、SCREEN(筛选排名)、USER(用户判断)、EXECUTION(执行增量)。
"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.performance_metrics import (
    direction_accuracy,
    interval_coverage,
    mae,
    rmse,
    top_n_excess_return,
    top_n_return,
)
from app.models.forecast import PredictionSnapshot, ReviewResult, ScreeningCandidate
from app.models.performance import MetricBatch, PerformanceMetric
from app.models.research import DecisionEntry, ResearchCase

logger = logging.getLogger(__name__)


class PerformanceService:
    def __init__(self, db: Session):
        self.db = db

    def compute_model_metrics(
        self, model_version_id: str, cutoff: date
    ) -> MetricBatch:
        preds = self.db.scalars(
            select(PredictionSnapshot).where(
                PredictionSnapshot.model_version_id == model_version_id,
                PredictionSnapshot.business_date <= cutoff,
                PredictionSnapshot.state == "SETTLED",
            )
        ).all()

        batch = MetricBatch(
            calculation_version="1.0.0",
            cutoff_date=cutoff,
            source_row_count=len(preds),
            status="SUCCESS",
        )
        self.db.add(batch)
        self.db.flush()

        predicted_returns = []
        actual_returns = []
        lowers = []
        uppers = []

        for pred in preds:
            review = self.db.scalars(
                select(ReviewResult).where(
                    ReviewResult.prediction_snapshot_id == pred.id
                )
            ).first()
            if review and review.actual_return is not None:
                predicted_returns.append(pred.median_return)
                actual_returns.append(review.actual_return)
                lowers.append(pred.lower_return)
                uppers.append(pred.upper_return)

        if predicted_returns:
            da = direction_accuracy(predicted_returns, actual_returns)
            self._save_metric(batch.id, "MODEL", model_version_id, "direction_accuracy", da.value, da.sample_count, cutoff)
            m = mae(predicted_returns, actual_returns)
            self._save_metric(batch.id, "MODEL", model_version_id, "mae", m.value, m.sample_count, cutoff)
            r = rmse(predicted_returns, actual_returns)
            self._save_metric(batch.id, "MODEL", model_version_id, "rmse", r.value, r.sample_count, cutoff)
            ic = interval_coverage(actual_returns, lowers, uppers)
            self._save_metric(batch.id, "MODEL", model_version_id, "interval_coverage", ic.value, ic.sample_count, cutoff)

        self.db.flush()
        return batch

    def compute_user_judgment_metrics(self, cutoff: date) -> MetricBatch:
        cases = self.db.scalars(
            select(ResearchCase).where(ResearchCase.created_at <= cutoff)
        ).all()

        batch = MetricBatch(
            calculation_version="1.0.0",
            cutoff_date=cutoff,
            source_row_count=len(cases),
            status="SUCCESS",
        )
        self.db.add(batch)
        self.db.flush()

        correct = 0
        total = 0
        for case in cases:
            review = self.db.scalars(
                select(ReviewResult).where(
                    ReviewResult.prediction_snapshot_id == case.prediction_snapshot_id
                )
            ).first()
            if review and review.actual_return is not None:
                total += 1
                if case.initial_direction == "BULLISH" and review.actual_return > 0.01:
                    correct += 1
                elif case.initial_direction == "BEARISH" and review.actual_return < -0.01:
                    correct += 1
                elif case.initial_direction == "NEUTRAL" and abs(review.actual_return) <= 0.01:
                    correct += 1

        accuracy = correct / total if total > 0 else None
        self._save_metric(batch.id, "USER", "ALL", "judgment_accuracy", accuracy, total, cutoff)
        self.db.flush()
        return batch

    def _save_metric(
        self, batch_id: str, scope: str, scope_id: str,
        name: str, value: float | None, sample_count: int, cutoff: date,
    ) -> None:
        metric = PerformanceMetric(
            batch_id=batch_id,
            scope=scope,
            scope_id=scope_id,
            metric_name=name,
            dimension_key="ALL",
            value=value,
            sample_count=sample_count,
            period_end=cutoff,
        )
        self.db.add(metric)

    def get_latest_metrics(self, scope: str | None = None) -> list[PerformanceMetric]:
        stmt = select(PerformanceMetric).order_by(PerformanceMetric.created_at.desc())
        if scope:
            stmt = stmt.where(PerformanceMetric.scope == scope)
        return list(self.db.scalars(stmt).limit(50).all())