"""正式预测服务:模型注册 + 不可改写的 10 日预测契约。

核心契约:
- create_formal_prediction 对 (business_date, symbol, model, horizon) 幂等,
  重复调用返回同一条 PredictionSnapshot,绝不原地改写;
- 预测输入只读取批次内已冻结的 DailyBar(按 batch_id),不再重新拉取行情;
- LLM 仅用于解释,不进入数值评分(本服务不涉及 LLM)。
"""
from __future__ import annotations

import json
import logging

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.forecasting import (
    HORIZON_DAYS,
    WINDOW_OBSERVATIONS,
    FLAT_THRESHOLD,
    ForecastEngine,
)
from app.models.forecast import DailyBar, MarketDataBatch, ModelVersion, PredictionSnapshot
from app.services.market_data_service import DEFAULT_INDEX_CODE

logger = logging.getLogger(__name__)

BASELINE_MODEL_NAME = "historical-10d-baseline"
BASELINE_MODEL_VERSION = "1.0.0"
BASELINE_FEATURE_VERSION = "daily-adjusted-v1"


def register_baseline_model(
    db: Session, training_cutoff=None, code_revision: str | None = None
) -> ModelVersion:
    """获取或创建历史基准模型版本(name+version 唯一)。"""
    existing = db.scalars(
        select(ModelVersion).where(
            ModelVersion.name == BASELINE_MODEL_NAME,
            ModelVersion.version == BASELINE_MODEL_VERSION,
        )
    ).first()
    if existing is not None:
        return existing

    params = json.dumps(
        {
            "horizon_days": HORIZON_DAYS,
            "window_observations": WINDOW_OBSERVATIONS,
            "flat_threshold": FLAT_THRESHOLD,
        },
        ensure_ascii=False,
    )
    model = ModelVersion(
        name=BASELINE_MODEL_NAME,
        version=BASELINE_MODEL_VERSION,
        feature_version=BASELINE_FEATURE_VERSION,
        parameters_json=params,
        training_cutoff=training_cutoff,
        code_revision=code_revision,
    )
    db.add(model)
    db.flush()
    return model


class ForecastService:
    """生成并持久化不可改写的正式预测快照。"""

    def __init__(self, db: Session):
        self.db = db

    def create_formal_prediction(
        self,
        frozen_batch,
        model: ModelVersion,
        symbol: str,
        horizon_days: int = HORIZON_DAYS,
        benchmark_symbol: str = DEFAULT_INDEX_CODE,
    ) -> PredictionSnapshot:
        batch = self.db.get(MarketDataBatch, frozen_batch.batch_id)
        if batch is None:
            raise ValueError(f"market data batch not found: {frozen_batch.batch_id}")
        business_date = batch.business_date

        existing = self.db.scalars(
            select(PredictionSnapshot).where(
                PredictionSnapshot.business_date == business_date,
                PredictionSnapshot.symbol == symbol,
                PredictionSnapshot.model_version_id == model.id,
                PredictionSnapshot.horizon_days == horizon_days,
            )
        ).first()
        if existing is not None:
            return existing

        stock_frame = self._load_bars_frame(batch.id, symbol)
        bench_frame = self._load_bars_frame(batch.id, benchmark_symbol)
        output = ForecastEngine(horizon_days).predict(stock_frame, bench_frame)

        snapshot = PredictionSnapshot(
            business_date=business_date,
            symbol=symbol,
            model_version_id=model.id,
            market_data_batch_id=batch.id,
            horizon_days=horizon_days,
            p_up=output.p_up,
            p_flat=output.p_flat,
            p_down=output.p_down,
            median_return=output.median_return,
            lower_return=output.lower_return,
            upper_return=output.upper_return,
            expected_excess_return=output.expected_excess_return,
            expected_mfe=output.expected_mfe,
            expected_mae=output.expected_mae,
            state="PENDING",
        )
        self.db.add(snapshot)
        self.db.commit()
        return snapshot

    def _load_bars_frame(self, batch_id: str, symbol: str) -> pd.DataFrame:
        bars = self.db.scalars(
            select(DailyBar)
            .where(
                DailyBar.market_data_batch_id == batch_id,
                DailyBar.symbol == symbol,
            )
            .order_by(DailyBar.date)
        ).all()
        return pd.DataFrame(
            [
                {"date": b.date, "close": b.close, "adj_factor": b.adj_factor}
                for b in bars
            ]
        )