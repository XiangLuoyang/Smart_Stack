"""单股研究读模型组合服务。

独立组合行情、K线、预测、技术指标、风险、LLM、历史预测与研究案例,
任何单一板块失败不影响其他板块;LLM 失败绝不阻塞量化数据。
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Protocol

import pandas as pd
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.forecast import ModelVersion, PredictionSnapshot
from app.models.research import ResearchCase
from app.schemas.stock_research import (
    DEGRADED,
    READY,
    UNAVAILABLE,
    CaseSummary,
    ForecastSection,
    HistoricalForecast,
    KlineBar,
    KlineSection,
    LlmSection,
    QuoteSection,
    RiskSection,
    StockResearchView,
    TechnicalSection,
)

logger = logging.getLogger(__name__)


class KlineProvider(Protocol):
    """K线数据提供者协议(可注入 fake)。"""

    def get_kline(self, symbol: str, days: int = 120) -> pd.DataFrame: ...


class LlmProvider(Protocol):
    """LLM 报告提供者协议(可注入 fake)。"""

    def get_llm_signal(self, symbol: str) -> dict | None: ...


class DefaultKlineProvider:
    """生产用 K线提供者:复用 MarketService。"""

    def __init__(self, db: Session):
        self.db = db

    def get_kline(self, symbol: str, days: int = 120) -> pd.DataFrame:
        from app.services.market_service import MarketService

        return MarketService(self.db).get_kline(symbol, days)


class DefaultLlmProvider:
    """生产用 LLM 提供者:读取 SignalService 中的 LLM 信号。"""

    def __init__(self, db: Session):
        self.db = db

    def get_llm_signal(self, symbol: str) -> dict | None:
        from app.models.signal import SOURCE_LLM
        from app.services.signal_service import SignalService

        svc = SignalService(self.db)
        sig = svc.get_latest(symbol, SOURCE_LLM)
        if sig is None:
            return None
        import json

        try:
            payload = json.loads(sig.payload_json)
        except (json.JSONDecodeError, TypeError):
            payload = {}
        return {
            "score": sig.score,
            "created_at": sig.created_at,
            "report_markdown": payload.get("report_markdown"),
        }


class StockResearchService:
    """组合单股研究视图,各板块独立容错。"""

    def __init__(
        self,
        db: Session,
        kline_provider: KlineProvider | None = None,
        llm_provider: LlmProvider | None = None,
    ):
        self.db = db
        self.kline_provider = kline_provider or DefaultKlineProvider(db)
        self.llm_provider = llm_provider or DefaultLlmProvider(db)

    def get(self, symbol: str, as_of: date | None = None) -> StockResearchView:
        as_of = as_of or date.today()
        view = StockResearchView(symbol=symbol, as_of=as_of)

        kline_df = self._compose_kline_and_quote(symbol, view)
        self._compose_technical(kline_df, view)
        self._compose_risk(kline_df, view)
        self._compose_forecast(symbol, as_of, view)
        self._compose_historical_forecasts(symbol, view)
        self._compose_llm(symbol, view)
        self._compose_cases(symbol, view)

        return view

    def _compose_kline_and_quote(
        self, symbol: str, view: StockResearchView
    ) -> pd.DataFrame | None:
        try:
            df = self.kline_provider.get_kline(symbol, days=130)
            if df is None or df.empty:
                return None
            bars: list[KlineBar] = []
            for _, row in df.iterrows():
                bar_date = row.get("Date") or row.get("date")
                if bar_date is None:
                    continue
                if isinstance(bar_date, str):
                    bar_date = date.fromisoformat(bar_date[:10])
                elif isinstance(bar_date, datetime):
                    bar_date = bar_date.date()
                elif hasattr(bar_date, "date"):
                    bar_date = bar_date.date()
                bars.append(
                    KlineBar(
                        date=bar_date,
                        open=float(row.get("Open", row.get("open", 0))),
                        high=float(row.get("High", row.get("high", 0))),
                        low=float(row.get("Low", row.get("low", 0))),
                        close=float(row.get("Close", row.get("close", 0))),
                        volume=float(row.get("Volume", row.get("volume", 0))),
                    )
                )
            if bars:
                view.kline = KlineSection(
                    status=READY, bars=bars, data_cutoff=bars[-1].date
                )
                view.data_cutoff = bars[-1].date
                last = bars[-1]
                prev_close = bars[-2].close if len(bars) >= 2 else None
                change_pct = (
                    ((last.close - prev_close) / prev_close * 100)
                    if prev_close
                    else None
                )
                view.quote = QuoteSection(
                    status=READY,
                    price=last.close,
                    prev_close=prev_close,
                    change_pct=change_pct,
                )
            return df
        except Exception as exc:
            logger.warning(f"K线组合失败 {symbol}: {exc}")
            return None

    def _compose_technical(
        self, kline_df: pd.DataFrame | None, view: StockResearchView
    ) -> None:
        if kline_df is None or kline_df.empty:
            return
        try:
            last = kline_df.iloc[-1]
            section = TechnicalSection(status=READY)
            section.rsi = _safe_float(last.get("RSI"))
            section.macd = _safe_float(last.get("MACD"))
            section.macd_signal = _safe_float(last.get("Signal_Line"))
            section.macd_histogram = _safe_float(last.get("MACD_Histogram"))
            section.ma5 = _safe_float(last.get("MA5"))
            section.ma20 = _safe_float(last.get("MA20"))
            section.ma60 = _safe_float(last.get("MA60"))
            section.bb_upper = _safe_float(last.get("BB_Upper"))
            section.bb_middle = _safe_float(last.get("BB_Middle"))
            section.bb_lower = _safe_float(last.get("BB_Lower"))
            if all(
                v is None
                for v in [
                    section.rsi, section.macd, section.ma5,
                    section.ma20, section.ma60,
                ]
            ):
                section.status = UNAVAILABLE
            view.technical = section
        except Exception as exc:
            logger.warning(f"技术指标组合失败: {exc}")

    def _compose_risk(
        self, kline_df: pd.DataFrame | None, view: StockResearchView
    ) -> None:
        if kline_df is None or kline_df.empty:
            return
        try:
            from app.engine.risk_metrics import RiskMetricsCalculator

            metrics = RiskMetricsCalculator().calculate(kline_df)
            vol = metrics.get("波动率")
            dd = metrics.get("最大回撤")
            sharpe = metrics.get("夏普比率")
            if vol == 0.0 and dd == 0.0 and sharpe == 0.0:
                view.risk = RiskSection(status=UNAVAILABLE)
            else:
                view.risk = RiskSection(
                    status=READY,
                    annualized_volatility=vol,
                    max_drawdown=dd,
                    sharpe_ratio=sharpe,
                )
        except Exception as exc:
            logger.warning(f"风险指标组合失败: {exc}")

    def _compose_forecast(
        self, symbol: str, as_of: date, view: StockResearchView
    ) -> None:
        try:
            stmt = (
                select(PredictionSnapshot)
                .where(
                    PredictionSnapshot.symbol == symbol,
                    PredictionSnapshot.business_date <= as_of,
                )
                .order_by(desc(PredictionSnapshot.business_date))
                .limit(1)
            )
            pred = self.db.scalars(stmt).first()
            if pred is None:
                return
            model = self.db.get(ModelVersion, pred.model_version_id)
            view.forecast = ForecastSection(
                status=READY,
                prediction_id=pred.id,
                business_date=pred.business_date,
                horizon_days=pred.horizon_days,
                model_name=model.name if model else None,
                model_version=model.version if model else None,
                p_up=pred.p_up,
                p_flat=pred.p_flat,
                p_down=pred.p_down,
                median_return=pred.median_return,
                lower_return=pred.lower_return,
                upper_return=pred.upper_return,
                expected_excess_return=pred.expected_excess_return,
                state=pred.state,
            )
        except Exception as exc:
            logger.warning(f"预测组合失败 {symbol}: {exc}")

    def _compose_historical_forecasts(
        self, symbol: str, view: StockResearchView
    ) -> None:
        try:
            stmt = (
                select(PredictionSnapshot)
                .where(PredictionSnapshot.symbol == symbol)
                .order_by(desc(PredictionSnapshot.business_date))
                .limit(20)
            )
            preds = self.db.scalars(stmt).all()
            view.historical_forecasts = [
                HistoricalForecast(
                    prediction_id=p.id,
                    business_date=p.business_date,
                    horizon_days=p.horizon_days,
                    median_return=p.median_return,
                    expected_excess_return=p.expected_excess_return,
                    state=p.state,
                )
                for p in preds
            ]
        except Exception as exc:
            logger.warning(f"历史预测组合失败 {symbol}: {exc}")

    def _compose_llm(self, symbol: str, view: StockResearchView) -> None:
        try:
            result = self.llm_provider.get_llm_signal(symbol)
            if result is None:
                view.llm = LlmSection(status=UNAVAILABLE)
                return
            created_at = result.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            view.llm = LlmSection(
                status=READY,
                report_markdown=result.get("report_markdown"),
                score=result.get("score"),
                created_at=created_at,
            )
        except Exception as exc:
            logger.warning(f"LLM 组合失败 {symbol}: {exc}")
            view.llm = LlmSection(status=UNAVAILABLE)

    def _compose_cases(self, symbol: str, view: StockResearchView) -> None:
        try:
            stmt = (
                select(ResearchCase)
                .where(ResearchCase.symbol == symbol)
                .order_by(desc(ResearchCase.created_at))
            )
            cases = self.db.scalars(stmt).all()
            for case in cases:
                summary = CaseSummary(
                    id=case.id,
                    symbol=case.symbol,
                    status=case.status,
                    initial_direction=case.initial_direction,
                    thesis=case.thesis,
                    confidence=case.confidence,
                    created_at=case.created_at,
                    closed_at=case.closed_at,
                )
                if case.status == "ACTIVE":
                    view.active_cases.append(summary)
                else:
                    view.closed_cases.append(summary)
        except Exception as exc:
            logger.warning(f"案例组合失败 {symbol}: {exc}")


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
        if pd.isna(f):
            return None
        return f
    except (TypeError, ValueError):
        return None