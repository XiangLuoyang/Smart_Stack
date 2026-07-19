"""FastAPI 依赖:数据库会话、共享 MarketService。"""
from __future__ import annotations

from fastapi import Depends

from app.db.base import SessionLocal, get_db
from app.services.market_service import MarketService

# 全局共享的内存行情缓存(单例,跨请求共享)
_global_market_service: MarketService | None = None


def get_market_service() -> MarketService:
    """返回共享 MarketService 实例(跨请求共享同一个内存缓存)。"""
    global _global_market_service
    if _global_market_service is None:
        _global_market_service = MarketService(SessionLocal())
    return _global_market_service


def get_market_service_with_db(db=Depends(get_db)) -> MarketService:
    """绑定请求级 db session 的 MarketService。"""
    svc = get_market_service()
    svc.db = db
    return svc


__all__ = ["get_db", "get_market_service", "get_market_service_with_db"]
