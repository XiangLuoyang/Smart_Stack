"""行情路由:报价、K 线、SSE 流。"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_market_service_with_db
from app.schemas.market import KlineBar, QuoteOut
from app.services.market_service import MarketService

router = APIRouter(prefix="/api/market", tags=["market"])


def _quote_to_out(symbol: str, market: MarketService) -> QuoteOut:
    q = market.get_quote(symbol)
    if q is None:
        return QuoteOut(symbol=symbol, price=0.0, ts=datetime.now())
    snap = market.latest_snapshot(symbol)
    prev_close = snap.prev_close if snap else None
    change_pct = (
        (q.price - prev_close) / prev_close * 100 if prev_close else None
    )
    return QuoteOut(
        symbol=q.symbol, price=q.price, ts=q.ts,
        bid=q.bid, ask=q.ask, prev_close=prev_close, change_pct=change_pct,
    )


@router.get("/quotes", response_model=list[QuoteOut])
def get_quotes(
    symbols: str = Query(..., description="逗号分隔的代码列表"),
    market: MarketService = Depends(get_market_service_with_db),
):
    syms = [s.strip() for s in symbols.split(",") if s.strip()]
    return [_quote_to_out(s, market) for s in syms]


@router.post("/refresh")
def refresh_quotes(
    symbols: str = Query(...),
    market: MarketService = Depends(get_market_service_with_db),
):
    syms = [s.strip() for s in symbols.split(",") if s.strip()]
    result = market.refresh_many(syms)
    return {"refreshed": list(result.keys()), "failed": [s for s in syms if s not in result]}


@router.post("/_debug/inject_quote")
def debug_inject_quote(
    symbol: str = Query(...),
    price: float = Query(...),
    market: MarketService = Depends(get_market_service_with_db),
):
    """[仅 DEBUG] 手动注入行情到内存缓存,用于纸面测试。生产关闭 DEBUG 即不可用。"""
    from datetime import datetime
    from fastapi import HTTPException
    from app.core.config import get_settings
    from app.engine.matching import Quote
    if not get_settings().debug:
        raise HTTPException(403, "调试端点仅在 DEBUG 模式可用")
    market.update_quote(Quote(symbol=symbol, price=price, ts=datetime.now()))
    return {"injected": symbol, "price": price}


@router.get("/kline", response_model=list[KlineBar])
def get_kline(
    symbol: str = Query(...),
    days: int = Query(default=120, ge=10, le=1000),
    db: Session = Depends(get_db),
):
    market = MarketService(db)
    df = market.get_kline(symbol, days=days)
    if df.empty:
        return []
    bars: list[KlineBar] = []
    for _, row in df.iterrows():
        d = row.get("Date")
        date_str = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)
        bars.append(KlineBar(
            date=date_str,
            open=float(row.get("Open", 0)),
            high=float(row.get("High", 0)),
            low=float(row.get("Low", 0)),
            close=float(row.get("Close", 0)),
            volume=float(row.get("Volume", 0)),
            ma5=float(row["MA5"]) if "MA5" in row and row["MA5"] == row["MA5"] else None,
            ma20=float(row["MA20"]) if "MA20" in row and row["MA20"] == row["MA20"] else None,
            ma60=float(row["MA60"]) if "MA60" in row and row["MA60"] == row["MA60"] else None,
        ))
    return bars


@router.get("/stream")
async def stream(
    request: Request,
    symbols: str = Query(..., description="订阅的代码,逗号分隔"),
    market: MarketService = Depends(get_market_service_with_db),
):
    """SSE 行情推送:每 5 秒广播一次最新缓存价。"""
    syms = [s.strip() for s in symbols.split(",") if s.strip()]

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            payload = []
            for s in syms:
                q = market.get_quote(s)
                if q:
                    payload.append({"symbol": s, "price": q.price, "ts": q.ts.isoformat()})
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            await asyncio.sleep(5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
