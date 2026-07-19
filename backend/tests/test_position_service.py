"""持仓服务测试:加权平均成本。"""
from __future__ import annotations

from app.services.position_service import PositionService


def test_buy_creates_position_with_avg_cost(db_session):
    svc = PositionService(db_session)
    pos = svc.apply_buy("acc1", "000001", 1000, 10.0)
    assert pos.qty == 1000
    assert pos.avg_cost == 10.0


def test_buy_updates_weighted_avg_cost(db_session):
    svc = PositionService(db_session)
    svc.apply_buy("acc1", "000001", 1000, 10.0)
    pos = svc.apply_buy("acc1", "000001", 1000, 12.0)
    assert pos.qty == 2000
    assert abs(pos.avg_cost - 11.0) < 1e-6


def test_sell_reduces_qty_keeps_avg_cost(db_session):
    svc = PositionService(db_session)
    svc.apply_buy("acc1", "000001", 1000, 10.0)
    pos = svc.apply_sell("acc1", "000001", 300, 11.0)
    assert pos.qty == 700
    assert pos.avg_cost == 10.0


def test_sell_to_zero_clears_position(db_session):
    svc = PositionService(db_session)
    svc.apply_buy("acc1", "000001", 1000, 10.0)
    pos = svc.apply_sell("acc1", "000001", 1000, 11.0)
    assert pos is None
    assert svc.get("acc1", "000001") is None
