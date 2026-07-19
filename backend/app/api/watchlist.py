"""自选股路由:用 JSON 文件持久化(本期单用户简化方案)。"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import DATA_DIR

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

_WATCHLIST_FILE = DATA_DIR / "watchlist.json"


def _load() -> list[str]:
    if not _WATCHLIST_FILE.exists():
        return []
    try:
        return json.loads(_WATCHLIST_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list[str]) -> None:
    _WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    _WATCHLIST_FILE.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")


class WatchlistAdd(BaseModel):
    symbol: str


@router.get("")
def list_watchlist() -> list[str]:
    return _load()


@router.post("")
def add_to_watchlist(payload: WatchlistAdd) -> list[str]:
    items = _load()
    if payload.symbol not in items:
        items.append(payload.symbol)
        _save(items)
    return items


@router.delete("/{symbol}")
def remove_from_watchlist(symbol: str) -> list[str]:
    items = _load()
    if symbol in items:
        items.remove(symbol)
        _save(items)
    return items
