from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class QuoteOut(BaseModel):
    symbol: str
    price: float
    ts: datetime
    bid: float | None = None
    ask: float | None = None
    prev_close: float | None = None
    change_pct: float | None = None


class KlineBar(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    ma5: float | None = None
    ma20: float | None = None
    ma60: float | None = None
