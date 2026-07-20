"""信号服务:读取 LSTM / LLM 分析结果,前端只读消费。

生成端(后台任务)把分析结果写入 signals 表,本服务只负责读。
本期信号生成采用懒触发:get_or_refresh 接口在缓存缺失时同步生成;
后续阶段可换成 APScheduler 定时刷新。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.signal import SOURCE_LLM, SOURCE_LSTM, Signal

logger = logging.getLogger(__name__)

# 信号缓存有效期:6 小时
SIGNAL_TTL = timedelta(hours=6)


class SignalService:
    def __init__(self, db: Session):
        self.db = db

    def get_latest(self, symbol: str, source: str) -> Signal | None:
        stmt = (
            select(Signal)
            .where(Signal.symbol == symbol, Signal.source == source)
            .order_by(desc(Signal.created_at))
            .limit(1)
        )
        return self.db.scalars(stmt).first()

    def get_all_sources(self, symbol: str) -> dict[str, dict]:
        """返回 {source: payload_dict}。"""
        result: dict[str, dict] = {}
        for source in (SOURCE_LSTM, SOURCE_LLM):
            sig = self.get_latest(symbol, source)
            if sig and (datetime.now() - sig.created_at) < SIGNAL_TTL:
                try:
                    result[source] = {
                        "score": sig.score,
                        "created_at": sig.created_at.isoformat(),
                        **json.loads(sig.payload_json),
                    }
                except json.JSONDecodeError:
                    logger.warning(f"信号 payload 解析失败 {symbol} {source}")
        return result

    def upsert(self, symbol: str, source: str, score: float, payload: dict) -> Signal:
        """写入新信号(简单 append,不覆盖历史)。"""
        sig = Signal(
            symbol=symbol,
            source=source,
            score=float(score),
            payload_json=json.dumps(payload, ensure_ascii=False),
            created_at=datetime.now(),
        )
        self.db.add(sig)
        self.db.commit()
        self.db.refresh(sig)
        return sig

    def refresh_lstm(self, symbol: str) -> dict | None:
        """触发 LSTM 信号生成(复用旧 src/models/prediction)。

        生成失败返回 None,不影响下单链路。
        """
        try:
            from src.models.prediction import ReturnPredictor
            predictor = ReturnPredictor()
            result = predictor.calculate_expected_return(
                symbol, datetime(2020, 1, 1), 30, 0.95
            )
            if result.get("error"):
                return None
            # Use annualized return as the headline score (more interpretable than daily).
            # Fall back to daily if the predictor didn't compute annualized.
            score = float(result.get("annualized_return") or result.get("expected_daily_return") or 0.0)
            self.upsert(symbol, SOURCE_LSTM, score, result)
            return result
        except Exception as e:
            logger.warning(f"LSTM 信号刷新失败 {symbol}: {e}")
            return None

    def refresh_llm(self, symbol: str) -> str | None:
        """触发 LLM 报告生成(复用旧 src/llm_analysis)。"""
        try:
            from app.llm_bridge import generate_llm_report
            report = generate_llm_report(symbol)
            if report:
                self.upsert(symbol, SOURCE_LLM, 0.0, {"report_markdown": report})
            return report
        except Exception as e:
            logger.warning(f"LLM 信号刷新失败 {symbol}: {e}")
            return None
