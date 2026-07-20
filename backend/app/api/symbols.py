"""Stock name and search routes for matching codes to company names."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.symbol_service import get_symbol_service

router = APIRouter(prefix="/api/symbols", tags=["symbols"])


@router.get("/search")
def search(q: str = Query(..., min_length=1, description="code prefix or name keyword")) -> list[dict]:
    """Search stocks by code prefix or name substring."""
    return get_symbol_service().search(q, limit=20)


@router.get("/name")
def names(codes: str = Query(..., description="comma-separated code list")) -> dict:
    """Batch lookup names. Returns {code: name}; unknown codes map to empty string."""
    svc = get_symbol_service()
    items = [c.strip() for c in codes.split(",") if c.strip()]
    return svc.get_names(items)