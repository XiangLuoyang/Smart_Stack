"""性能指标 API。"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.performance_service import PerformanceService

router = APIRouter(prefix="/api/performance", tags=["performance"])


@router.get("/metrics")
def get_metrics(scope: str | None = Query(None), db: Session = Depends(get_db)):
    svc = PerformanceService(db)
    metrics = svc.get_latest_metrics(scope)
    return [
        {
            "id": m.id,
            "scope": m.scope,
            "scope_id": m.scope_id,
            "metric_name": m.metric_name,
            "value": m.value,
            "sample_count": m.sample_count,
            "period_end": m.period_end.isoformat() if m.period_end else None,
        }
        for m in metrics
    ]


@router.post("/compute")
def compute_metrics(
    model_version_id: str = Query(...),
    cutoff: date = Query(None),
    db: Session = Depends(get_db),
):
    svc = PerformanceService(db)
    batch = svc.compute_model_metrics(model_version_id, cutoff or date.today())
    db.commit()
    return {"batch_id": batch.id, "status": batch.status, "row_count": batch.source_row_count}