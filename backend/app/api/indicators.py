"""技术指标路由:RSI/MACD/均线/布林/KDJ + 综合买卖信号。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.market_service import MarketService

router = APIRouter(prefix="/api/market", tags=["indicators"])


@router.get("/indicators")
def get_indicators(
    symbol: str = Query(...),
    days: int = Query(default=120, ge=20, le=1000),
    db: Session = Depends(get_db),
):
    """返回技术指标分析与买卖信号。"""
    market = MarketService(db)
    df = market.get_kline(symbol, days=days)
    if df.empty:
        return {"symbol": symbol, "ready": False, "reason": "无行情数据"}

    last = df.iloc[-1]
    close = float(last.get("Close", 0))
    prev_close = float(df.iloc[-2]["Close"]) if len(df) >= 2 else close

    def _f(v):
        try:
            return float(v) if v == v else None
        except Exception:
            return None

    rsi_v = _f(last.get("RSI"))
    macd_v = _f(last.get("MACD"))
    signal_v = _f(last.get("Signal_Line"))
    hist_v = _f(last.get("MACD_Histogram"))
    ma5 = _f(last.get("MA5"))
    ma20 = _f(last.get("MA20"))
    ma60 = _f(last.get("MA60"))

    signals = []
    if rsi_v is not None:
        if rsi_v < 30:
            signals.append({"name": "RSI 超卖", "tag": "buy", "detail": "RSI=%.1f<30" % rsi_v})
        elif rsi_v > 70:
            signals.append({"name": "RSI 超买", "tag": "sell", "detail": "RSI=%.1f>70" % rsi_v})
    if macd_v is not None and signal_v is not None:
        if macd_v > signal_v and hist_v and hist_v > 0:
            signals.append({"name": "MACD 金叉", "tag": "buy", "detail": "MACD 上穿信号线"})
        elif macd_v < signal_v and hist_v and hist_v < 0:
            signals.append({"name": "MACD 死叉", "tag": "sell", "detail": "MACD 下穿信号线"})
    if ma5 is not None and ma20 is not None:
        if ma5 > ma20 and close > ma5:
            signals.append({"name": "均线多头", "tag": "buy", "detail": "MA5>MA20 且价格在均线之上"})
        elif ma5 < ma20 and close < ma5:
            signals.append({"name": "均线空头", "tag": "sell", "detail": "MA5<MA20 且价格在均线之下"})

    kdj = None
    try:
        low9 = df["Low"].rolling(window=9, min_periods=1).min()
        high9 = df["High"].rolling(window=9, min_periods=1).max()
        rsv = (df["Close"] - low9) / (high9 - low9).replace(0, float("nan")) * 100
        k = rsv.ewm(com=2, adjust=False).mean()
        d = k.ewm(com=2, adjust=False).mean()
        j = 3 * k - 2 * d
        kdj = {"k": _f(k.iloc[-1]), "d": _f(d.iloc[-1]), "j": _f(j.iloc[-1])}
    except Exception:
        kdj = None

    return {
        "symbol": symbol,
        "ready": True,
        "close": close,
        "prev_close": prev_close,
        "change_pct": (close - prev_close) / prev_close * 100 if prev_close else None,
        "indicators": {
            "rsi": rsi_v,
            "macd": macd_v,
            "macd_signal": signal_v,
            "macd_hist": hist_v,
            "ma5": ma5,
            "ma20": ma20,
            "ma60": ma60,
            "bb_upper": _f(last.get("BB_Upper")),
            "bb_middle": _f(last.get("BB_Middle")),
            "bb_lower": _f(last.get("BB_Lower")),
            "kdj": kdj,
        },
        "signals": signals,
    }