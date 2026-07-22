"""Phase 3 端到端验收:研究案例 -> 预览 -> 确认 -> 成交 -> T+1 可卖。"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
import app.models  # noqa: F401
from app.engine.matching import Quote
from app.models.account import Account
from app.models.forecast import ModelVersion, PredictionSnapshot
from app.models.position import Position
from app.models.research import ResearchCase
from app.models.settlement_lot import SettlementLot
from app.services.order_confirmation_service import OrderConfirmationService
from app.services.settlement_service import SettlementService


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_operations_e2e(db):
    """完整操作闭环:案例 -> 预览 -> 确认 -> 持仓 -> T+1。"""
    account = Account(name="personal", cash=1000000.0)
    db.add(account)
    db.flush()

    model = ModelVersion(name="test", version="1.0")
    db.add(model)
    db.flush()

    pred = PredictionSnapshot(
        business_date=date(2026, 7, 21), symbol="000001",
        model_version_id=model.id, horizon_days=10,
        p_up=0.5, p_flat=0.2, p_down=0.3,
        median_return=0.02, lower_return=-0.01, upper_return=0.05,
        expected_excess_return=0.015, expected_mfe=0.03, expected_mae=-0.01,
        state="PENDING",
    )
    db.add(pred)
    db.flush()

    case = ResearchCase(
        symbol="000001", prediction_snapshot_id=pred.id,
        status="ACTIVE", initial_direction="BULLISH",
        thesis="demand up", expected_return_lower=0.01, expected_return_upper=0.05,
        counterargument="priced in", invalidation_condition="break low",
        planned_entry=10.0, target_price=10.5, stop_price=9.5,
        confidence=4, frozen_analysis_json="{}",
    )
    db.add(case)
    db.flush()

    svc = OrderConfirmationService(db)
    quote = Quote(symbol="000001", price=10.0, ts=_utcnow())

    preview = svc.preview(
        account_id=account.id, symbol="000001", side="BUY", qty=200,
        order_type="LIMIT", price=10.0,
        research_case_id=case.id, quote=quote,
    )
    assert preview.confirmation_token

    result = svc.confirm(
        preview.id, preview.confirmation_token, "e2e-key-1", quote=quote,
    )
    assert result["status"] == "FILLED"

    pos = db.scalars(select(Position).where(Position.symbol == "000001")).first()
    assert pos.qty == 200
    assert pos.avg_cost == pytest.approx(10.0)
    assert account.cash == pytest.approx(1000000.0 - 2000.0)

    lots = db.scalars(select(SettlementLot).where(SettlementLot.symbol == "000001")).all()
    assert len(lots) == 1
    assert lots[0].remaining_qty == 200

    settlement_svc = SettlementService(db)
    today = _utcnow().date()
    assert settlement_svc.sellable_qty(account.id, "000001", today) == 0
    tomorrow = today + timedelta(days=1)
    assert settlement_svc.sellable_qty(account.id, "000001", tomorrow) == 200