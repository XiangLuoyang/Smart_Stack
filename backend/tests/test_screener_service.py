"""筛选服务测试:完整排名持久化、幂等与排序。"""
from __future__ import annotations

from datetime import date

from app.services.screener_service import ScreenerService


def test_scan_persists_successes_and_failures(db_session, screening_pipeline):
    run = ScreenerService(db_session, screening_pipeline).run(
        date(2026, 7, 21), screening_pipeline.model_id
    )
    assert run.total_count == 3
    assert run.success_count == 2
    assert run.failure_count == 1
    assert run.status == "PARTIAL"

    rows = ScreenerService(db_session, screening_pipeline).list_candidates(run.id)
    assert [r.rank for r in rows if r.status == "SUCCESS"] == [1, 2]
    assert next(r.failure_reason for r in rows if r.status == "FAILED") == "STALE_DATA"


def test_ranking_orders_by_excess_return_desc(db_session, screening_pipeline):
    run = ScreenerService(db_session, screening_pipeline).run(
        date(2026, 7, 21), screening_pipeline.model_id
    )
    rows = ScreenerService(db_session, screening_pipeline).list_candidates(run.id)
    successes = [r for r in rows if r.status == "SUCCESS"]
    # 000001 超额 0.05 排第 1,600000 超额 0.02 排第 2
    assert successes[0].symbol == "000001"
    assert successes[0].rank == 1
    assert successes[1].symbol == "600000"
    assert successes[1].rank == 2


def test_run_is_idempotent(db_session, screening_pipeline):
    svc = ScreenerService(db_session, screening_pipeline)
    first = svc.run(date(2026, 7, 21), screening_pipeline.model_id)
    second = svc.run(date(2026, 7, 21), screening_pipeline.model_id)
    assert first.id == second.id