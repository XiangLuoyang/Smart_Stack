"""正式预测服务测试:幂等、持久化与模型注册。"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np
import pytest

from app.models.forecast import (
    DailyBar,
    MarketDataBatch,
    ModelVersion,
    PredictionSnapshot,
)
from app.services.forecast_service import (
    ForecastService,
    register_baseline_model,
)
from app.services.market_data_service import FrozenMarketBatch


def _price_series(n, base, seed):
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0, 0.01, n)
    return base * np.cumprod(1.0 + steps)


def _insert_bars(db, batch_id, symbol, as_of, prices):
    n = len(prices)
    dates = [as_of - timedelta(days=i) for i in range(n - 1, -1, -1)]
    for d, p in zip(dates, prices):
        db.add(
            DailyBar(
                market_data_batch_id=batch_id,
                symbol=symbol,
                date=d,
                open=float(p),
                high=float(p),
                low=float(p),
                close=float(p),
                volume=1000.0,
                adj_factor=1.0,
            )
        )
    db.flush()


@pytest.fixture
def model(db_session):
    m = ModelVersion(
        name="historical-10d-baseline",
        version="1.0.0",
        feature_version="daily-adjusted-v1",
    )
    db_session.add(m)
    db_session.flush()
    return m


@pytest.fixture
def frozen_batch(db_session):
    as_of = date(2026, 7, 21)
    batch = MarketDataBatch(
        business_date=as_of,
        source="fake",
        cutoff_time=datetime(2026, 7, 21, 15, 0),
        status="SUCCESS",
        row_count=260,
        checksum="0" * 64,
        failures_json="{}",
        universe_snapshot_id=None,
    )
    db_session.add(batch)
    db_session.flush()
    _insert_bars(db_session, batch.id, "000001", as_of, _price_series(130, 10.0, seed=1))
    _insert_bars(db_session, batch.id, "000300", as_of, _price_series(130, 4000.0, seed=2))
    db_session.commit()
    return FrozenMarketBatch(
        batch_id=batch.id,
        universe_snapshot_id="",
        valid_symbols=("000001", "000300"),
        failures={},
    )


def test_formal_prediction_cannot_be_overwritten(db_session, frozen_batch, model):
    svc = ForecastService(db_session)
    first = svc.create_formal_prediction(frozen_batch, model, "000001")
    second = svc.create_formal_prediction(frozen_batch, model, "000001")
    assert first.id == second.id


def test_formal_prediction_values_persisted(db_session, frozen_batch, model):
    svc = ForecastService(db_session)
    snap = svc.create_formal_prediction(frozen_batch, model, "000001")
    assert snap.horizon_days == 10
    assert abs(snap.p_up + snap.p_flat + snap.p_down - 1.0) < 1e-9
    assert snap.state == "PENDING"
    assert snap.model_version_id == model.id
    assert snap.market_data_batch_id == frozen_batch.batch_id


def test_register_baseline_model_is_idempotent(db_session):
    first = register_baseline_model(db_session)
    second = register_baseline_model(db_session)
    assert first.id == second.id
    assert first.name == "historical-10d-baseline"
    assert first.version == "1.0.0"