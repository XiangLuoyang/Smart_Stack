"""信号源路由:只读 + 手动刷新。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.signal import SignalOut
from app.services.signal_service import SignalService

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/{symbol}", response_model=SignalOut)
def get_signal(symbol: str, db: Session = Depends(get_db)):
    svc = SignalService(db)
    data = svc.get_all_sources(symbol)
    return SignalOut(
        symbol=symbol,
        lstm=data.get("LSTM"),
        llm=data.get("LLM"),
    )


@router.post("/refresh")
def refresh_signal(
    symbol: str,
    source: str = "ALL",  # ALL / LSTM / LLM
    db: Session = Depends(get_db),
):
    svc = SignalService(db)
    refreshed = {}
    if source in ("ALL", "LSTM"):
        result = svc.refresh_lstm(symbol)
        refreshed["LSTM"] = "ok" if result else "failed"
    if source in ("ALL", "LLM"):
        result = svc.refresh_llm(symbol)
        refreshed["LLM"] = "ok" if result else "failed"
    if not refreshed:
        raise HTTPException(400, f"未知 source: {source}")
    return {"symbol": symbol, "refreshed": refreshed}
