"""到期结算服务测试:实际表现计算、幂等与缺价处理。"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from app.models.forecast import PredictionSnapshot, ReviewResult
from app.services.review_service import ReviewService


def test_settlement_records_actuals(db_session, due_prediction, bars):
    result = ReviewService(db_session, bars).settle_due(date(2026, 8, 4))
    assert result.settled == 1
    review = db_session.scalar(select(ReviewResult))
    assert review.actual_return == pytest.approx(0.08)
    assert review.direction_correct is True
    assert review.benchmark_excess == pytest.approx(0.07)
    assert review.state == "SETTLED"


def test_settlement_is_idempotent(db_session, due_prediction, bars):
    svc = ReviewService(db_session, bars)
    first = svc.settle_due(date(2026, 8, 4))
    second = svc.settle_due(date(2026, 8, 4))
    assert first.settled == 1
    assert second.settled == 0
    assert second.pending_data == 0


def test_not_due_yet_is_skipped(db_session, due_prediction, bars):
    # 到期日为 2026-08-04,早于该日期不结算
    result = ReviewService(db_session, bars).settle_due(date(2026, 8, 3))
    assert result.settled == 0
    assert db_session.scalar(select(ReviewResult)) is None


def test_missing_maturity_price_marks_pending_data(db_session, due_prediction, empty_bars):
    result = ReviewService(db_session, empty_bars).settle_due(date(2026, 8, 4))
    assert result.settled == 0
    assert result.pending_data == 1
    assert db_session.scalar(select(ReviewResult)) is None
    refreshed = db_session.get(PredictionSnapshot, due_prediction.id)
    assert refreshed.state == "PENDING_DATA"