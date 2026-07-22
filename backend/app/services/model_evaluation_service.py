"""模型评估与晋升服务:walk-forward 评估 + 晋升门控。"""
from __future__ import annotations

import json
import logging
from datetime import date

from sqlalchemy.orm import Session

from app.models.performance import ModelEvaluationRun, ModelPromotionDecision

logger = logging.getLogger(__name__)

PROMOTION_GATES = {
    "direction_accuracy_min": 0.45,
    "max_mae": 0.05,
    "min_sample_count": 30,
    "excess_return_positive": True,
}


class ModelEvaluationService:
    def __init__(self, db: Session):
        self.db = db

    def create_evaluation(
        self,
        candidate_model_id: str,
        baseline_model_id: str,
        metrics: dict,
        folds: list | None = None,
    ) -> ModelEvaluationRun:
        run = ModelEvaluationRun(
            candidate_model_id=candidate_model_id,
            baseline_model_id=baseline_model_id,
            folds_json=json.dumps(folds or [], default=str),
            metrics_json=json.dumps(metrics, default=str),
            status="COMPLETED",
        )
        self.db.add(run)
        self.db.flush()
        return run

    def evaluate_promotion(
        self,
        evaluation_run_id: str,
        candidate_metrics: dict,
        created_by: str = "system",
    ) -> ModelPromotionDecision:
        run = self.db.get(ModelEvaluationRun, evaluation_run_id)
        if run is None:
            raise ValueError("EVALUATION_NOT_FOUND")

        gate_results = {}
        all_passed = True

        da = candidate_metrics.get("direction_accuracy")
        if da is not None:
            passed = da >= PROMOTION_GATES["direction_accuracy_min"]
            gate_results["direction_accuracy"] = {"value": da, "threshold": PROMOTION_GATES["direction_accuracy_min"], "passed": passed}
            all_passed = all_passed and passed

        mae_val = candidate_metrics.get("mae")
        if mae_val is not None:
            passed = mae_val <= PROMOTION_GATES["max_mae"]
            gate_results["mae"] = {"value": mae_val, "threshold": PROMOTION_GATES["max_mae"], "passed": passed}
            all_passed = all_passed and passed

        sample = candidate_metrics.get("sample_count", 0)
        passed = sample >= PROMOTION_GATES["min_sample_count"]
        gate_results["sample_count"] = {"value": sample, "threshold": PROMOTION_GATES["min_sample_count"], "passed": passed}
        all_passed = all_passed and passed

        decision = ModelPromotionDecision(
            evaluation_run_id=evaluation_run_id,
            candidate_model_id=run.candidate_model_id,
            baseline_model_id=run.baseline_model_id,
            gate_decisions_json=json.dumps(gate_results, default=str),
            approved=all_passed,
            created_by=created_by,
        )
        self.db.add(decision)
        self.db.flush()
        return decision