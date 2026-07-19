"""APScheduler 定时任务:行情拉取、限价单撮合巡检。

交易时段外不拉行情、不撮合(避免节假日空跑),但仍允许手动触发。
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
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
