"""研究案例服务测试:冻结分析、追加式事件、决策链与关闭语义。"""
from __future__ import annotations

import json
from datetime import date

import pytest
from sqlalchemy import select

from app.models.forecast import ModelVersion, PredictionSnapshot
from app.models.research import ResearchCase
from app.schemas.research import CaseCreate, DecisionCreate, EvidenceCreate
from app.services.research_service import ResearchDomainError, ResearchService


class FakeAnalysisReader:
    """可控分析读取器:返回预设 payload,创建后改写不影响已冻结快照。"""

    def __init__(self, payload):
        self.payload = payload

    def snapshot(self, symbol):
        return self.payload


@pytest.fixture
def analysis_reader():
    return FakeAnalysisReader({"technical": {"rsi": 52.0}, "risk": {"vol": 0.2}})


@pytest.fixture
def prediction(db_session):
    model = ModelVersion(name="historical-10d-baseline", version="1.0.0")
    db_session.add(model)
    db_session.flush()
    pred = PredictionSnapshot(
        business_date=date(2026, 7, 21),
        symbol="000001",
        model_version_id=model.id,
        horizon_days=10,
        p_up=0.4, p_flat=0.2, p_down=0.4,
        median_return=0.01, lower_return=-0.03, upper_return=0.05,
        expected_excess_return=0.02, expected_mfe=0.04, expected_mae=-0.02,
        state="PENDING",
    )
    db_session.add(pred)
    db_session.commit()
    return pred


def _case_payload(prediction, **overrides):
    base = dict(
        prediction_snapshot_id=prediction.id,
        direction="BULLISH",
        thesis="需求改善",
        expected_return_lower=0.03,
        expected_return_upper=0.12,
        counterargument="价格已反映",
        invalidation_condition="跌破20日低点",
        planned_entry=10.0,
        target_price=11.2,
        stop_price=9.4,
        confidence=4,
    )
    base.update(overrides)
    return CaseCreate(**base)


@pytest.fixture
def research_case(db_session, prediction):
    case = ResearchCase(
        symbol="000001",
        prediction_snapshot_id=prediction.id,
        initial_direction="BULLISH",
        thesis="需求改善",
        expected_return_lower=0.03,
        expected_return_upper=0.12,
        counterargument="价格已反映",
        invalidation_condition="跌破20日低点",
        planned_entry=10.0,
        target_price=11.2,
        stop_price=9.4,
        confidence=4,
        frozen_analysis_json="{}",
    )
    db_session.add(case)
    db_session.commit()
    return case


def test_create_case_freezes_current_analysis(db_session, prediction, analysis_reader):
    case = ResearchService(db_session, analysis_reader).create_case(_case_payload(prediction))
    analysis_reader.payload["technical"]["rsi"] = 99
    frozen = json.loads(case.frozen_analysis_json)
    assert frozen["technical"]["rsi"] == 52.0  # 冻结值不随后续改写变化
    assert case.status == "ACTIVE"
    assert case.symbol == "000001"
    assert len(case.decision_entries) == 1  # 初始决策已写入
    assert case.decision_entries[0].direction == "BULLISH"


def test_create_case_rejects_bad_bullish_price_order(db_session, prediction, analysis_reader):
    service = ResearchService(db_session, analysis_reader)
    with pytest.raises(ResearchDomainError) as exc:
        service.create_case(_case_payload(prediction, stop_price=12.0))  # stop > entry
    assert exc.value.code == "INVALID_PRICE_ORDER"
    assert db_session.scalars(select(ResearchCase)).all() == []


def test_create_case_rejects_invalid_direction(db_session, prediction, analysis_reader):
    service = ResearchService(db_session, analysis_reader)
    with pytest.raises(ResearchDomainError) as exc:
        service.create_case(_case_payload(prediction, direction="SIDEWAYS"))
    assert exc.value.code == "INVALID_DIRECTION"


def test_create_case_requires_existing_prediction(db_session, analysis_reader):
    service = ResearchService(db_session, analysis_reader)
    with pytest.raises(ResearchDomainError) as exc:
        service.create_case(_case_payload(type("P", (), {"id": "missing"})()))
    assert exc.value.code == "PREDICTION_NOT_FOUND"


def test_append_decision_preserves_prior_record(db_session, research_case):
    service = ResearchService(db_session)
    old = service.append_decision(
        research_case.id, DecisionCreate(direction="BULLISH", action="WATCH", rationale="等待", confidence=3)
    )
    new = service.append_decision(
        research_case.id, DecisionCreate(direction="NEUTRAL", action="NO_ACTION", rationale="逻辑减弱", confidence=2)
    )
    assert old.id != new.id and new.supersedes_id == old.id


def test_append_decision_supersedes_initial_decision(db_session, prediction, analysis_reader):
    service = ResearchService(db_session, analysis_reader)
    case = service.create_case(_case_payload(prediction))
    initial = case.decision_entries[0]
    new = service.append_decision(
        case.id, DecisionCreate(direction="NEUTRAL", action="NO_ACTION", rationale="减弱", confidence=2)
    )
    assert new.supersedes_id == initial.id


def test_append_evidence_orders_by_created_at(db_session, research_case):
    service = ResearchService(db_session)
    service.append_evidence(
        research_case.id,
        EvidenceCreate(stance="SUPPORT", category="EARNINGS", content="盈利上修", observed_date=date(2026, 7, 21)),
    )
    service.append_evidence(
        research_case.id,
        EvidenceCreate(stance="OPPOSE", category="VALUATION", content="估值过高", observed_date=date(2026, 7, 22)),
    )
    assert [e.stance for e in research_case.evidence_entries] == ["SUPPORT", "OPPOSE"]


def test_closed_case_rejects_appends(db_session, research_case):
    service = ResearchService(db_session)
    service.close_case(research_case.id)
    assert research_case.status == "CLOSED"
    assert research_case.closed_at is not None
    with pytest.raises(ResearchDomainError) as exc:
        service.append_evidence(
            research_case.id,
            EvidenceCreate(stance="SUPPORT", category="X", content="x", observed_date=date(2026, 7, 22)),
        )
    assert exc.value.code == "CASE_CLOSED"


def test_create_case_rolls_back_when_commit_fails(
    db_session, prediction, analysis_reader, monkeypatch
):
    service = ResearchService(db_session, analysis_reader)

    def boom():
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(db_session, "commit", boom)
    with pytest.raises(RuntimeError):
        service.create_case(_case_payload(prediction))
    assert db_session.scalars(select(ResearchCase)).all() == []