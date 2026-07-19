"""回测路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.backtest import BacktestRunOut, BacktestRunRequest
from app.services.backtest_service import BacktestService
from app.services.market_service import MarketService

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.post("/run", response_model=BacktestRunOut)
def run_backtest(payload: BacktestRunRequest, db: Session = Depends(get_db)):
    market = MarketService(db)
    df, _ = market.adaptor.load_kline(
        payload.symbol,
        start_date=payload.start.strftime("%Y%m%d"),
        end_date=payload.end.strftime("%Y%m%d"),
    )
    if df.empty:
        raise HTTPException(400, f"无法获取 {payload.symbol} 历史数据")
    svc = BacktestService(db)
    try:
        run = svc.run(
            symbol=payload.symbol,
            strategy_name=payload.strategy_name,
            params=payload.params,
            df=df,
            start=payload.start,
            end=payload.end,
            initial_cash=payload.initial_cash,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return run


@router.get("/runs", response_model=list[BacktestRunOut])
def list_runs(limit: int = 50, db: Session = Depends(get_db)):
    return BacktestService(db).list_runs(limit=limit)


@router.get("/runs/{run_id}", response_model=BacktestRunOut)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = BacktestService(db).get(run_id)
    if not run:
        raise HTTPException(404, "回测记录不存在")
    return run
