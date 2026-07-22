"""阶段二端到端验收:筛选 -> 单股研究 -> 案例 -> 证据 -> 决策 -> 结算 -> 复盘。

证明完整研究闭环:
- 单股研究视图各板块独立;
- 案例创建冻结分析快照;
- 证据/决策追加不可改写;
- 到期结算写入自动结果;
- 复盘笔记不修改市场事实。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.models  # noqa: F401
from app.models.forecast import (
    DailyBar,
    MarketDataBatch,
    ModelVersion,
    PredictionSnapshot,
    TradingCalendar as TradingCalendarRow,
)


BUSINESS_DATE = date(2026, 7, 21)
MATURITY_DATE = date(2026, 8, 4)


def _populate_calendar(db):
    holidays = {
        date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3),
        date(2026, 10, 4), date(2026, 10, 5), date(2026, 10, 6),
        date(2026, 10, 7),
    }
    d = date(2026, 1, 1)
    while d <= date(2026, 12, 31):
        if d.weekday() < 5 and d not in holidays:
            db.add(TradingCalendarRow(session_date=d))
        d += timedelta(days=1)
    db.commit()


def _seed_data(db):
    """插入批次、模型、预测、日线数据。"""
    batch = MarketDataBatch(
        business_date=BUSINESS_DATE,
        source="e2e",
        cutoff_time=datetime(2026, 7, 21, 15, 0),
        status="SUCCESS",
        row_count=10,
        checksum="0" * 64,
    )
    db.add(batch)
    db.flush()

    model = ModelVersion(name="historical-10d-baseline", version="1.0.0")
    db.add(model)
    db.flush()

    pred = PredictionSnapshot(
        business_date=BUSINESS_DATE,
        symbol="000001",
        model_version_id=model.id,
        market_data_batch_id=batch.id,
        horizon_days=10,
        p_up=0.45,
        p_flat=0.20,
        p_down=0.35,
        median_return=0.02,
        lower_return=-0.01,
        upper_return=0.05,
        expected_excess_return=0.015,
        expected_mfe=0.03,
        expected_mae=-0.01,
        state="PENDING",
    )
    db.add(pred)
    db.flush()

    entry_price = 10.0
    maturity_price = 10.25
    db.add(DailyBar(
        market_data_batch_id=batch.id, symbol="000001",
        date=BUSINESS_DATE, open=entry_price, high=entry_price,
        low=entry_price, close=entry_price, volume=1e6, adj_factor=1.0,
    ))
    db.add(DailyBar(
        market_data_batch_id=batch.id, symbol="000001",
        date=MATURITY_DATE, open=maturity_price, high=maturity_price,
        low=maturity_price, close=maturity_price, volume=1e6, adj_factor=1.0,
    ))
    db.commit()
    return pred


@pytest.fixture
def db_session():
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
def client(db_session):
    from fastapi.testclient import TestClient
    from app.api.deps import get_db
    from app.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_research_loop_e2e(client, db_session):
    """完整研究闭环:研究视图 -> 案例 -> 证据 -> 决策 -> 结算 -> 复盘。"""
    _populate_calendar(db_session)
    pred = _seed_data(db_session)

    # 1. 单股研究视图
    stock = client.get("/api/research/stocks/000001").json()
    assert stock["symbol"] == "000001"
    assert stock["forecast"]["status"] == "READY"
    assert stock["forecast"]["horizon_days"] == 10
    assert stock["forecast"]["prediction_id"] == pred.id

    # 2. 创建研究案例
    case_resp = client.post("/api/research/cases", json={
        "prediction_snapshot_id": pred.id,
        "direction": "BULLISH",
        "thesis": "demand improvement drives upside",
        "expected_return_lower": 1.0,
        "expected_return_upper": 5.0,
        "counterargument": "already priced in",
        "invalidation_condition": "break 20d low",
        "planned_entry": 10.0,
        "target_price": 10.5,
        "stop_price": 9.5,
        "confidence": 4,
    })
    assert case_resp.status_code == 201
    case = case_resp.json()
    assert case["status"] == "ACTIVE"
    assert case["initial_direction"] == "BULLISH"
    case_id = case["id"]

    # 3. 追加证据
    ev_resp = client.post(f"/api/research/cases/{case_id}/evidence", json={
        "stance": "SUPPORT",
        "category": "EARNINGS",
        "content": "Q2 earnings beat consensus by 15%",
        "source_label": "annual report",
        "observed_date": "2026-07-22",
    })
    assert ev_resp.status_code == 201

    # 4. 追加决策(观点演变)
    dec_resp = client.post(f"/api/research/cases/{case_id}/decisions", json={
        "direction": "BULLISH",
        "action": "PLAN_BUY",
        "rationale": "earnings confirm thesis, upgrading from watch to plan buy",
        "confidence": 4,
    })
    assert dec_resp.status_code == 201
    decision = dec_resp.json()
    assert decision["supersedes_id"] is not None  # supersedes initial decision

    # 5. 验证案例详情包含事件
    detail = client.get(f"/api/research/cases/{case_id}").json()
    assert len(detail["evidence_entries"]) == 1
    assert len(detail["decision_entries"]) == 2  # initial + new

    # 6. 到期结算
    settle_resp = client.post("/api/reviews/settle", json={"as_of": "2026-08-04"})
    assert settle_resp.status_code == 200
    assert settle_resp.json()["settled"] == 1

    # 7. 验证结算结果
    review_detail = client.get(f"/api/reviews/{pred.id}").json()
    assert review_detail["review"]["actual_return"] == pytest.approx(0.025, abs=1e-6)
    assert review_detail["review"]["direction_correct"] is True

    # 8. 追加复盘笔记(不修改市场事实)
    note_resp = client.post(f"/api/reviews/{pred.id}/notes", json={
        "attribution": "direction correct, magnitude slightly underestimated",
        "error_tags": ["MODEL_MAGNITUDE"],
        "discipline_followed": True,
    })
    assert note_resp.status_code == 201

    # 9. 验证市场事实未被修改
    after = client.get(f"/api/reviews/{pred.id}").json()
    assert after["review"]["actual_return"] == pytest.approx(0.025, abs=1e-6)
    assert len(after["notes"]) == 1

    # 10. 关闭案例
    close_resp = client.post(f"/api/research/cases/{case_id}/close")
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "CLOSED"

    # 11. 关闭后追加被拒绝
    late_ev = client.post(f"/api/research/cases/{case_id}/evidence", json={
        "stance": "NEUTRAL",
        "category": "MISC",
        "content": "late evidence",
        "observed_date": "2026-08-05",
    })
    assert late_ev.status_code == 409