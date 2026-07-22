"""研究案例 append-only 事件模型的 schema 不变量测试。"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.forecast import ModelVersion, PredictionSnapshot
from app.models.research import DecisionEntry, EvidenceEntry, ResearchCase, ReviewNote


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


def _valid_case_attrs(prediction):
    return dict(
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


@pytest.fixture
def research_case(db_session, prediction):
    case = ResearchCase(**_valid_case_attrs(prediction))
    db_session.add(case)
    db_session.commit()
    return case


def test_case_requires_initial_decision(db_session, prediction):
    """缺少初始决策字段(方向/论点等 NOT NULL)的案例无法提交。"""
    case = ResearchCase(symbol="000001", prediction_snapshot_id=prediction.id)
    db_session.add(case)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_valid_case_persists_with_active_status(db_session, prediction):
    case = ResearchCase(**_valid_case_attrs(prediction))
    db_session.add(case)
    db_session.commit()
    assert case.status == "ACTIVE"
    assert case.closed_at is None
    assert case.prediction.symbol == "000001"


def test_events_are_ordered_by_created_at(db_session, research_case):
    db_session.add_all([
        EvidenceEntry(
            research_case_id=research_case.id, stance="SUPPORT", category="EARNINGS",
            content="盈利上修", source_label="USER", observed_date=date(2026, 7, 21),
        ),
        EvidenceEntry(
            research_case_id=research_case.id, stance="OPPOSE", category="VALUATION",
            content="估值过高", source_label="USER", observed_date=date(2026, 7, 22),
        ),
    ])
    db_session.commit()
    assert [e.stance for e in research_case.evidence_entries] == ["SUPPORT", "OPPOSE"]


def test_decision_chain_links_via_supersedes(db_session, research_case):
    first = DecisionEntry(
        research_case_id=research_case.id, direction="BULLISH", action="WATCH",
        rationale="等待", confidence=3,
    )
    db_session.add(first)
    db_session.commit()
    second = DecisionEntry(
        research_case_id=research_case.id, direction="NEUTRAL", action="NO_ACTION",
        rationale="逻辑减弱", confidence=2, supersedes_id=first.id,
    )
    db_session.add(second)
    db_session.commit()
    decisions = research_case.decision_entries
    assert [d.action for d in decisions] == ["WATCH", "NO_ACTION"]
    assert decisions[1].supersedes_id == decisions[0].id


def test_review_note_stores_tag_json(db_session, research_case):
    note = ReviewNote(
        research_case_id=research_case.id, content="误判需求强度",
        attribution_json='{"thesis": 0.6}', error_tags_json='["OVERCONFIDENCE"]',
    )
    db_session.add(note)
    db_session.commit()
    assert research_case.review_notes[0].content == "误判需求强度"