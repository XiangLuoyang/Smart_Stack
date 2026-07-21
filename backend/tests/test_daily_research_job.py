"""每日研究管线编排测试:session 拥有权、幂等与异常回滚。"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.jobs.daily_research import run_daily_research, settle_matured_forecasts
from app.models.forecast import MarketDataBatch, PredictionSnapshot
from app.models.forecast import TradingCalendar as TradingCalendarRow
from app.services.forecast_service import register_baseline_model
from app.services.market_data_service import FrozenMarketBatch


class SessionFactory:
    """计数 session 工厂:记录 opened/closed。"""

    def __init__(self, engine):
        self.opened = 0
        self.closed = 0
        self._maker = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def __call__(self):
        self.opened += 1
        session = self._maker()
        original_close = session.close

        def counting_close():
            self.closed += 1
            original_close()

        session.close = counting_close
        return session


def _populate_calendar(session):
    holidays = {
        date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3),
        date(2026, 10, 4), date(2026, 10, 5), date(2026, 10, 6),
        date(2026, 10, 7),
    }
    d = date(2026, 1, 1)
    while d <= date(2026, 12, 31):
        if d.weekday() < 5 and d not in holidays:
            session.add(TradingCalendarRow(session_date=d))
        d += timedelta(days=1)


def _make_prediction(session, batch_id, model_id, symbol, excess):
    pred = PredictionSnapshot(
        business_date=date(2026, 7, 21),
        symbol=symbol,
        model_version_id=model_id,
        market_data_batch_id=batch_id,
        horizon_days=10,
        p_up=0.4, p_flat=0.2, p_down=0.4,
        median_return=0.01, lower_return=-0.03, upper_return=0.05,
        expected_excess_return=excess, expected_mfe=0.04, expected_mae=-0.02,
        state="PENDING",
    )
    session.add(pred)
    session.flush()
    return pred


class LocalFakePipeline:
    def __init__(self, batch_id, model_id, predictions, failures):
        self.batch_id = batch_id
        self.model_id = model_id
        self._predictions = predictions
        self._failures = failures

    def freeze(self, business_date):
        return FrozenMarketBatch(
            batch_id=self.batch_id,
            universe_snapshot_id="",
            valid_symbols=tuple(self._predictions.keys()),
            failures=dict(self._failures),
        )

    def predict(self, frozen, model_version_id, symbol):
        return self._predictions[symbol]


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        yield SessionFactory(engine)
    finally:
        engine.dispose()


@pytest.fixture
def pipeline():
    """返回一个按 session 构造管线的工厂。"""

    def factory(session):
        _populate_calendar(session)
        batch = MarketDataBatch(
            business_date=date(2026, 7, 21),
            source="fake",
            cutoff_time=datetime(2026, 7, 21, 15, 0),
            status="SUCCESS",
            row_count=260,
            checksum="0" * 64,
            failures_json="{}",
            universe_snapshot_id=None,
        )
        session.add(batch)
        session.flush()
        model = register_baseline_model(session)
        pred1 = _make_prediction(session, batch.id, model.id, "000001", 0.05)
        pred2 = _make_prediction(session, batch.id, model.id, "600000", 0.02)
        return LocalFakePipeline(
            batch.id, model.id, {"000001": pred1, "600000": pred2}, {}
        )

    return factory


def test_daily_job_uses_one_owned_session(session_factory, pipeline):
    summary = run_daily_research(date(2026, 7, 21), session_factory, pipeline)
    assert summary.screening_status == "SUCCESS"
    assert session_factory.opened == session_factory.closed == 1
    assert summary.success_count == 2
    assert summary.failure_count == 0


def test_settle_uses_one_owned_session(session_factory):
    summary = settle_matured_forecasts(date(2026, 8, 4), session_factory)
    assert summary.settled == 0
    assert session_factory.opened == session_factory.closed == 1


def test_run_rolls_back_and_closes_on_error(session_factory):
    def bad_pipeline(session):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        run_daily_research(date(2026, 7, 21), session_factory, bad_pipeline)
    assert session_factory.opened == session_factory.closed == 1