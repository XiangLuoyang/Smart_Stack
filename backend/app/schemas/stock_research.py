"""单股研究读模型 Pydantic schema。

每个 section 独立标注状态(READY/STALE/UNAVAILABLE/DEGRADED),
缺失数据映射为 None 而非 0;LLM 失败不阻塞量化板块。
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

# Section status constants
READY = "READY"
STALE = "STALE"
UNAVAILABLE = "UNAVAILABLE"
DEGRADED = "DEGRADED"


class QuoteSection(BaseModel):
    status: str = UNAVAILABLE
    price: float | None = None
    prev_close: float | None = None
    change_pct: float | None = None
    ts: datetime | None = None


class KlineBar(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class KlineSection(BaseModel):
    status: str = UNAVAILABLE
    bars: list[KlineBar] = []
    data_cutoff: date | None = None


class ForecastSection(BaseModel):
    status: str = UNAVAILABLE
    prediction_id: str | None = None
    business_date: date | None = None
    horizon_days: int | None = None
    model_name: str | None = None
    model_version: str | None = None
    p_up: float | None = None
    p_flat: float | None = None
    p_down: float | None = None
    median_return: float | None = None
    lower_return: float | None = None
    upper_return: float | None = None
    expected_excess_return: float | None = None
    state: str | None = None


class TechnicalSection(BaseModel):
    status: str = UNAVAILABLE
    rsi: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    ma5: float | None = None
    ma20: float | None = None
    ma60: float | None = None
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None


class RiskSection(BaseModel):
    status: str = UNAVAILABLE
    annualized_volatility: float | None = None
    max_drawdown: float | None = None
    sharpe_ratio: float | None = None


class LlmSection(BaseModel):
    status: str = UNAVAILABLE
    report_markdown: str | None = None
    score: float | None = None
    created_at: datetime | None = None


class CaseSummary(BaseModel):
    id: str
    symbol: str
    status: str
    initial_direction: str
    thesis: str
    confidence: int
    created_at: datetime
    closed_at: datetime | None = None


class HistoricalForecast(BaseModel):
    prediction_id: str
    business_date: date
    horizon_days: int
    median_return: float
    expected_excess_return: float
    state: str


class StockResearchView(BaseModel):
    symbol: str
    as_of: date
    data_cutoff: date | None = None
    quote: QuoteSection = QuoteSection()
    kline: KlineSection = KlineSection()
    forecast: ForecastSection = ForecastSection()
    technical: TechnicalSection = TechnicalSection()
    risk: RiskSection = RiskSection()
    llm: LlmSection = LlmSection()
    historical_forecasts: list[HistoricalForecast] = []
    active_cases: list[CaseSummary] = []
    closed_cases: list[CaseSummary] = []