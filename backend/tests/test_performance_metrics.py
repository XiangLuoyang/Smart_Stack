"""性能指标计算测试。"""
from __future__ import annotations

import pytest

from app.engine.performance_metrics import (
    direction_accuracy,
    interval_coverage,
    mae,
    model_metrics,
    ranking_metrics,
    rmse,
    top_n_excess_return,
    top_n_return,
)


class TestModelMetrics:
    def test_direction_accuracy_known(self):
        result = direction_accuracy([0.10, -0.05, 0.02], [0.08, 0.01, -0.01])
        assert result.value == pytest.approx(1 / 3)
        assert result.sample_count == 3

    def test_mae_known(self):
        result = mae([0.10, -0.05, 0.02], [0.08, 0.01, -0.01])
        expected = (0.02 + 0.06 + 0.03) / 3
        assert result.value == pytest.approx(expected)

    def test_rmse_known(self):
        result = rmse([0.10, -0.05, 0.02], [0.08, 0.01, -0.01])
        import numpy as np
        expected = float(np.sqrt(np.mean([0.02**2, 0.06**2, 0.03**2])))
        assert result.value == pytest.approx(expected)

    def test_interval_coverage_known(self):
        result = interval_coverage(
            actual=[0.08, 0.01, -0.01],
            lower=[0.0, -0.10, -0.02],
            upper=[0.15, 0.0, 0.05],
        )
        assert result.value == pytest.approx(2 / 3)

    def test_missing_data_excluded(self):
        result = direction_accuracy([0.10, None, 0.02], [0.08, 0.01, None])
        assert result.sample_count == 1

    def test_empty_returns_none(self):
        result = direction_accuracy([], [])
        assert result.value is None
        assert result.sample_count == 0


class TestRankingMetrics:
    def test_top10_equal_weighted(self):
        result = top_n_return(ranks=[1, 2, 11], actual=[0.10, 0.00, 0.50], top_n=10)
        assert result.value == pytest.approx(0.05)
        assert result.sample_count == 2

    def test_top10_excess(self):
        result = top_n_excess_return(
            ranks=[1, 2, 11], actual=[0.10, 0.00, 0.50],
            benchmark_return=0.02, top_n=10,
        )
        assert result.value == pytest.approx(0.03)

    def test_model_metrics_dict(self):
        out = model_metrics(
            pred=[0.10, -0.05, 0.02],
            actual=[0.08, 0.01, -0.01],
            lower=[0.0, -0.10, -0.02],
            upper=[0.15, 0.0, 0.05],
        )
        assert "direction_accuracy" in out
        assert "interval_coverage" in out

    def test_ranking_metrics_dict(self):
        out = ranking_metrics(ranks=[1, 2, 11], actual=[0.10, 0.00, 0.50], benchmark=0.02)
        assert out["top_n_return"].value == pytest.approx(0.05)
        assert out["top_n_excess_return"].value == pytest.approx(0.03)

class TestExecutionIncrement:
    def test_positive_increment(self):
        from app.engine.performance_metrics import execution_increment
        result = execution_increment([0.02, 0.01, -0.01], [0.03, 0.015, 0.0])
        assert result.value == pytest.approx((0.01 + 0.005 + 0.01) / 3)
        assert result.sample_count == 3

    def test_empty_returns_none(self):
        from app.engine.performance_metrics import execution_increment
        result = execution_increment([], [])
        assert result.value is None