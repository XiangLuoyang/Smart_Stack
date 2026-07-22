"""健康检查端点:组件级状态。"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db

router = APIRouter(prefix="/api/health", tags=["meta"])


@router.get("")
def health_check(db: Session = Depends(get_db)):
    components = {}
    try:
        db.execute(text("SELECT 1"))
        components["database"] = "OK"
    except Exception:
        components["database"] = "FAILED"

    overall = "OK" if all(v == "OK" for v in components.values()) else "DEGRADED"
    return {
        "status": overall,
        "components": components,
        "ts": datetime.now(timezone.utc).isoformat(),
    }