"""单股研究读模型测试。

验证:
- 各板块独立组合,LLM 失败不阻塞量化板块;
- 缺失数据映射为 None/UNAVAILABLE 而非 0;
- 技术指标与风险指标数值正确;
- 预测 horizon_days == 10;
- 案例按 ACTIVE/CLOSED 分组。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.models  # noqa: F401
from app.engine.technical import TechnicalIndicatorCalculator
from app.models.forecast import ModelVersion, PredictionSnapshot
from app.models.research import DecisionEntry, ResearchCase
from app.schemas.stock_research import READY, UNAVAILABLE
from app.services.stock_research_service import StockResearchService


# ---------------- Fakes ----------------


def _make_kline_df(rows: int = 130) -> pd.DataFrame:
    """生成确定性 K线 DataFrame,带真实技术指标。"""
    np.random.seed(42)
    dates = pd.date_range(end="2026-07-21", periods=rows, freq="B")
    close = 10.0 + np.cumsum(np.random.randn(rows) * 0.1)
    df = pd.DataFrame(
        {
            "Date": dates,
            "Open": close - np.random.rand(rows) * 0.05,
            "High": close + np.random.rand(rows) * 0.1,
            "Low": close - np.random.rand(rows) * 0.1,
            "Close": close,
            "Volume": np.random.randint(1000, 100000, rows).astype(float),
        }
    )
    calc = TechnicalIndicatorCalculator()
    return calc.add_all_indicators(df)


class FakeKlineProvider:
    def __init__(self, df: pd.DataFrame | None = None):
        self.df = df if df is not None else _make_kline_df()

    def get_kline(self, symbol: str, days: int = 120) -> pd.DataFrame:
        return self.df


class RaisingLlmProvider:
    def get_llm_signal(self, symbol: str) -> dict | None:
        raise RuntimeError("LLM service down")


class NoneLlmProvider:
    def get_llm_signal(self, symbol: str) -> dict | None:
        return None


class FakeLlmProvider:
    def __init__(self, payload: dict):
        self._payload = payload

    def get_llm_signal(self, symbol: str) -> dict | None:
        return self._payload


# ---------------- Fixtures ----------------


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def kline_df():
    return _make_kline_df()


@pytest.fixture
def seeded_db(db):
    """插入模型版本 + 预测快照 + 研究案例。"""
    model = ModelVersion(name="historical-10d-baseline", version="1.0.0")
    db.add(model)
    db.flush()

    pred = PredictionSnapshot(
        business_date=date(2026, 7, 21),
        symbol="000001",
        model_version_id=model.id,
        horizon_days=10,
        p_up=0.45,
        p_flat=0.20,
        p_down=0.35,
        median_return=0.012,
        lower_return=-0.02,
        upper_return=0.05,
        expected_excess_return=0.03,
        expected_mfe=0.04,
        expected_mae=-0.015,
        state="PENDING",
    )
    db.add(pred)
    db.flush()

    case = ResearchCase(
        symbol="000001",
        prediction_snapshot_id=pred.id,
        status="ACTIVE",
        initial_direction="BULLISH",
        thesis="demand improvement",
        expected_return_lower=0.03,
        expected_return_upper=0.12,
        counterargument="priced in",
        invalidation_condition="break 20d low",
        planned_entry=10.0,
        target_price=11.2,
        stop_price=9.4,
        confidence=4,
        frozen_analysis_json="{}",
    )
    db.add(case)
    db.flush()

    closed_case = ResearchCase(
        symbol="000001",
        prediction_snapshot_id=pred.id,
        status="CLOSED",
        initial_direction="BEARISH",
        thesis="valuation stretched",
        expected_return_lower=-0.08,
        expected_return_upper=-0.02,
        counterargument="momentum strong",
        invalidation_condition="new high",
        planned_entry=10.5,
        target_price=9.5,
        stop_price=11.0,
        confidence=3,
        frozen_analysis_json="{}",
        closed_at=datetime(2026, 7, 20, 10, 0, 0),
    )
    db.add(closed_case)
    db.commit()
    return db


# ---------------- Tests ----------------


class TestStockResearchSections:
    def test_sections_are_independent_and_llm_failure_does_not_block(
        self, seeded_db, kline_df
    ):
        svc = StockResearchService(
            seeded_db,
            kline_provider=FakeKlineProvider(kline_df),
            llm_provider=RaisingLlmProvider(),
        )
        view = svc.get("000001", as_of=date(2026, 7, 21))

        assert view.forecast.status == READY
        assert view.forecast.horizon_days == 10
        assert view.technical.status == READY
        assert view.risk.status == READY
        assert view.llm.status == UNAVAILABLE
        assert view.llm.report_markdown is None

    def test_technical_rsi_matches_kline(self, seeded_db, kline_df):
        svc = StockResearchService(
            seeded_db,
            kline_provider=FakeKlineProvider(kline_df),
            llm_provider=NoneLlmProvider(),
        )
        view = svc.get("000001", as_of=date(2026, 7, 21))

        expected_rsi = float(kline_df["RSI"].iloc[-1])
        assert view.technical.rsi == pytest.approx(expected_rsi, abs=1e-6)

    def test_risk_annualized_volatility_positive(self, seeded_db, kline_df):
        svc = StockResearchService(
            seeded_db,
            kline_provider=FakeKlineProvider(kline_df),
            llm_provider=NoneLlmProvider(),
        )
        view = svc.get("000001", as_of=date(2026, 7, 21))

        assert view.risk.annualized_volatility is not None
        assert view.risk.annualized_volatility > 0

    def test_missing_forecast_is_unavailable_not_zero(self, db, kline_df):
        svc = StockResearchService(
            db,
            kline_provider=FakeKlineProvider(kline_df),
            llm_provider=NoneLlmProvider(),
        )
        view = svc.get("999999", as_of=date(2026, 7, 21))

        assert view.forecast.status == UNAVAILABLE
        assert view.forecast.median_return is None
        assert view.forecast.p_up is None

    def test_llm_ready_when_provider_returns(self, seeded_db, kline_df):
        llm = FakeLlmProvider(
            {
                "score": 0.7,
                "created_at": datetime(2026, 7, 21, 8, 0),
                "report_markdown": "# Report\nBullish.",
            }
        )
        svc = StockResearchService(
            seeded_db,
            kline_provider=FakeKlineProvider(kline_df),
            llm_provider=llm,
        )
        view = svc.get("000001", as_of=date(2026, 7, 21))

        assert view.llm.status == READY
        assert view.llm.report_markdown == "# Report\nBullish."
        assert view.llm.score == 0.7

    def test_cases_split_active_closed(self, seeded_db, kline_df):
        svc = StockResearchService(
            seeded_db,
            kline_provider=FakeKlineProvider(kline_df),
            llm_provider=NoneLlmProvider(),
        )
        view = svc.get("000001", as_of=date(2026, 7, 21))

        assert len(view.active_cases) == 1
        assert view.active_cases[0].status == "ACTIVE"
        assert len(view.closed_cases) == 1
        assert view.closed_cases[0].status == "CLOSED"

    def test_empty_kline_gives_unavailable_sections(self, db):
        svc = StockResearchService(
            db,
            kline_provider=FakeKlineProvider(pd.DataFrame()),
            llm_provider=NoneLlmProvider(),
        )
        view = svc.get("000001", as_of=date(2026, 7, 21))

        assert view.kline.status == UNAVAILABLE
        assert view.technical.status == UNAVAILABLE
        assert view.risk.status == UNAVAILABLE
        assert view.quote.status == UNAVAILABLE

    def test_data_cutoff_from_kline(self, seeded_db, kline_df):
        svc = StockResearchService(
            seeded_db,
            kline_provider=FakeKlineProvider(kline_df),
            llm_provider=NoneLlmProvider(),
        )
        view = svc.get("000001", as_of=date(2026, 7, 21))

        expected_cutoff = kline_df["Date"].iloc[-1].date()
        assert view.data_cutoff == expected_cutoff
        assert view.kline.data_cutoff == expected_cutoff