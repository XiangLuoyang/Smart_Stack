"""FastAPI 应用入口。

启动方式:
    cd backend
    uvicorn app.main:app --reload --port 8000

启动后访问:
    http://localhost:8000/docs   Swagger UI
    http://localhost:8000/api/accounts  账户 API
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import accounts, backtest, forecasts, indicators, market, orders, research, reviews, risk_rules, screener, signals, symbols, watchlist
from pathlib import Path as _Path
from dotenv import load_dotenv as _load_dotenv
_PROJECT_ROOT = _Path(__file__).resolve().parents[2]
# Load root .env first (real LLM_API_KEY lives there); backend/.env must not override it
_load_dotenv(_PROJECT_ROOT / ".env", override=True)
_load_dotenv(_PROJECT_ROOT / "backend" / ".env", override=False)
from app.core.config import get_settings
from app.db.base import init_db
from app.jobs import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期:启动建表 + 调度器,退出清理。"""
    init_db()
    sched = start_scheduler()
    logger.info("Smart Stack 操盘工作台后端已启动")
    try:
        yield
    finally:
        stop_scheduler()
        logger.info("后端已停止")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="2.0.0",
        description="纸面操盘工作台 API",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(accounts.router)
    app.include_router(orders.router)
    app.include_router(market.router)
    app.include_router(signals.router)
    app.include_router(risk_rules.router)
    app.include_router(backtest.router)
    app.include_router(screener.router)
    app.include_router(symbols.router)
    app.include_router(indicators.router)
    app.include_router(watchlist.router)
    app.include_router(reviews.router)
    app.include_router(forecasts.router)
    app.include_router(research.router)

    @app.get("/api/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "name": settings.app_name, "version": "2.0.0"}

    return app


app = create_app()
