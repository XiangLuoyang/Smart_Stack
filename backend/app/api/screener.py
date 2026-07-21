"""沪深300筛选路由:查询历史筛选运行与完整排名。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.forecast import MarketDataBatch, ModelVersion
from app.schemas.screener import ScreeningCandidateRead, ScreeningRunRead
from app.services.screener_service import ScreenerService

router = APIRouter(prefix="/api/screener", tags=["screener"])


def _to_read(db: Session, run, with_candidates: bool) -> ScreeningRunRead:
    model = db.get(ModelVersion, run.model_version_id)
    model_version = f"{model.name}@{model.version}" if model else None

    data_cutoff = None
    if run.market_data_batch_id:
        batch = db.get(MarketDataBatch, run.market_data_batch_id)
        data_cutoff = batch.cutoff_time if batch else None

    candidates: list[ScreeningCandidateRead] = []
    top10: list[ScreeningCandidateRead] = []
    if with_candidates:
        svc = ScreenerService(db)
        rows = svc.list_candidates(run.id)
        candidates = [ScreeningCandidateRead.model_validate(r) for r in rows]
        top10 = [c for c in candidates if c.status == "SUCCESS"][:10]

    return ScreeningRunRead(
        id=run.id,
        business_date=run.business_date,
        model_version_id=run.model_version_id,
        model_version=model_version,
        status=run.status,
        total_count=run.total_count,
        success_count=run.success_count,
        failure_count=run.failure_count,
        data_cutoff=data_cutoff,
        candidates=candidates,
        top10=top10,
    )


@router.get("/runs", response_model=list[ScreeningRunRead])
def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """按业务日倒序列出历史筛选运行(不含候选明细)。"""
    svc = ScreenerService(db)
    runs = svc.list_runs(limit=limit, offset=offset)
    return [_to_read(db, run, with_candidates=False) for run in runs]


@router.get("/runs/{run_id}", response_model=ScreeningRunRead)
def get_run(run_id: str, db: Session = Depends(get_db)):
    """获取单次筛选运行,含完整候选排名与 Top10。"""
    svc = ScreenerService(db)
    run = svc.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="screening run not found")
    return _to_read(db, run, with_candidates=True)