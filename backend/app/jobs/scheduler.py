"""APScheduler 定时任务:行情拉取、限价单撮合巡检。

交易时段外不拉行情、不撮合(避免节假日空跑),但仍允许手动触发。
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.api.deps import get_market_service
from app.db.base import SessionLocal
from app.engine.market_hours import is_trading_time
from app.services.order_service import OrderService

logger = logging.getLogger(__name__)


_scheduler: BackgroundScheduler | None = None


def _job_refresh_quotes() -> None:
    """只在交易时段拉行情。"""
    if not is_trading_time():
        return
    market = get_market_service()
    symbols = market.all_symbols()
    if not symbols:
        return
    market.db = SessionLocal()
    try:
        market.refresh_many(symbols)
    finally:
        market.db.close()


def _job_scan_pending_orders() -> None:
    """限价单 + 止损止盈巡检。"""
    if not is_trading_time():
        return
    market = get_market_service()
    db = SessionLocal()
    try:
        market.db = db
        quotes = market.get_quotes(market.all_symbols())
        if quotes:
            filled = OrderService(db).scan_pending_orders(quotes)
            if filled:
                logger.info(f"限价单巡检成交 {filled} 笔")
    finally:
        db.close()


def _session_factory():
    """为每个任务创建一个独立 session。"""
    return SessionLocal()


def _production_pipeline(session):
    """生产用筛选管线:复用行情适配器。"""
    from app.services.market_service import MarketDataAdaptor
    from app.services.screener_service import ScreeningPipeline

    return ScreeningPipeline(session, MarketDataAdaptor())


def _job_daily_research() -> None:
    """收盘后生成正式预测与筛选。"""
    from app.jobs.daily_research import run_daily_research

    try:
        summary = run_daily_research(None, _session_factory, _production_pipeline)
        logger.info(
            f"每日研究完成 {summary.business_date}: {summary.screening_status} "
            f"成功 {summary.success_count} 失败 {summary.failure_count} 结算 {summary.settled}"
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"每日研究任务异常: {exc}", exc_info=True)


def _job_settlement() -> None:
    """结算到期预测。"""
    from app.jobs.daily_research import settle_matured_forecasts

    try:
        summary = settle_matured_forecasts(None, _session_factory)
        logger.info(f"到期结算完成: 结算 {summary.settled} 待数据 {summary.pending_data}")
    except Exception as exc:  # noqa: BLE001
        logger.error(f"结算任务异常: {exc}", exc_info=True)


def start_scheduler() -> BackgroundScheduler:
    """启动后台调度器(幂等)。"""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    from app.core.config import get_settings

    settings = get_settings().market
    sched = BackgroundScheduler(timezone="Asia/Shanghai")

    sched.add_job(
        _job_refresh_quotes,
        IntervalTrigger(seconds=settings.quote_poll_seconds),
        id="refresh_quotes",
        max_instances=1,
        coalesce=True,
    )
    sched.add_job(
        _job_scan_pending_orders,
        IntervalTrigger(seconds=settings.limit_order_match_seconds),
        id="scan_pending_orders",
        max_instances=1,
        coalesce=True,
    )
    sched.add_job(
        _job_daily_research,
        CronTrigger(hour=settings.daily_research_hour, minute=settings.daily_research_minute),
        id="daily_research",
        max_instances=1,
        coalesce=True,
    )
    sched.add_job(
        _job_settlement,
        CronTrigger(hour=settings.settlement_hour, minute=settings.settlement_minute),
        id="settlement",
        max_instances=1,
        coalesce=True,
    )

    sched.start()
    _scheduler = sched
    logger.info(
        f"调度器已启动:行情 {settings.quote_poll_seconds}s / 巡检 {settings.limit_order_match_seconds}s"
    )
    return sched


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
