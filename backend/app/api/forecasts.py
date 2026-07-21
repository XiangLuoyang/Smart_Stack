"""预测历史路由:按 symbol 查询正式预测快照(最新在前)。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.forecast import PredictionSnapshot
from app.schemas.forecast import PredictionSnapshotRead

router = APIRouter(prefix="/api/forecasts", tags=["forecasts"])


@router.get("/{symbol}", response_model=list[PredictionSnapshotRead])
def get_forecast_history(symbol: str, db: Session = Depends(get_db)):
    """返回某只股票的全部正式预测,按业务日倒序(最新在前)。"""
    rows = db.scalars(
        select(PredictionSnapshot)
        .where(PredictionSnapshot.symbol == symbol)
        .order_by(PredictionSnapshot.business_date.desc())
    ).all()
    return list(rows)