"""每日研究管线编排:冻结行情 -> 筛选预测 -> 结算到期预测。

每个任务函数自己创建一个 session,通过服务提交,异常时回滚,finally 关闭;
绝不把 session 挂到进程级单例上。session_factory 与 pipeline 均为可调用对象,
便于测试注入计数工厂与受控管线。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from app.services.forecast_service import register_baseline_model
from app.services.review_service import DatabaseBarSource, ReviewService, SettlementSummary
from app.services.screener_service import ScreenerService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DailyRunSummary:
    business_date: date
    screening_status: str
    screening_run_id: str | None
    success_count: int
    failure_count: int
    settled: int


def run_daily_research(business_date, session_factory, pipeline) -> DailyRunSummary:
    """执行一次完整的每日研究管线。

    pipeline: 可调用对象,接收一个 Session 返回 ScreeningPipeline(亦可直接传实例)。
    session_factory: 可调用对象,创建并拥有一个新 Session。
    """
    if business_date is None:
        business_date = date.today()

    session = session_factory()
    try:
        screening_pipeline = pipeline(session) if callable(pipeline) else pipeline
        model = register_baseline_model(session)
        run = ScreenerService(session, screening_pipeline).run(business_date, model.id)
        settlement = ReviewService(session, DatabaseBarSource(session)).settle_due(
            business_date
        )
        return DailyRunSummary(
            business_date=business_date,
            screening_status=run.status,
            screening_run_id=run.id,
            success_count=run.success_count,
            failure_count=run.failure_count,
            settled=settlement.settled,
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def settle_matured_forecasts(as_of, session_factory) -> SettlementSummary:
    """结算所有截至 as_of 已到期的预测。"""
    if as_of is None:
        as_of = date.today()

    session = session_factory()
    try:
        return ReviewService(session, DatabaseBarSource(session)).settle_due(as_of)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()