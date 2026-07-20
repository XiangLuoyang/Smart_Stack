"""沪深300选股路由:启动扫描 + 查询进度/结果。"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.screener_service import get_screener

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.post("/scan")
def start_scan(top_n: int = Query(default=10, ge=1, le=50)):
    """启动(或复用)后台选股扫描。返回当前状态。"""
    msg = get_screener().start(top_n=top_n)
    return {"action": msg, **get_screener().status()}


@router.get("/status")
def status():
    """查询扫描进度与结果(任务在跑时返回进度,完成后返回 Top N)。"""
    return get_screener().status()