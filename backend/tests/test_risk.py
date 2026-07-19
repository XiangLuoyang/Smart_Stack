"""风控引擎测试。"""
from __future__ import annotations

from app.engine.risk import (
    AccountSnapshot,
    RiskEngine,
    RC_INSUFFICIENT_HOLDING,
    RC_MAX_SINGLE,
    RC_DAILY_LIMIT,
)
from app.models.risk_rule import RiskRule


def make_rule(**kwargs) -> RiskRule:
    defaults = dict(
        account_id="acc1",
        max_position_pct=0.9,
        max_single_pct=0.3,
        stop_loss_pct=0.08,
        take_profit_pct=0.20,
        max_daily_trades=20,
    )
    defaults.update(kwargs)
    return RiskRule(**defaults)


def make_snapshot(**kwargs) -> AccountSnapshot:
    defaults = dict(
        cash=1_000_000.0,
        total_market_value=0.0,
        target_holding_value=0.0,
        target_holding_qty=0.0,
        today_trade_count=0,
    )
    defaults.update(kwargs)
    return AccountSnapshot(**defaults)


def test_buy_passes_clean_account():
    engine = RiskEngine()
    result = engine.pre_trade_check(
        make_rule(), make_snapshot(), "BUY", "000001", 1000, 10.0
    )
    assert result.passed


def test_sell_rejected_insufficient_holding():
    engine = RiskEngine()
    result = engine.pre_trade_check(
        make_rule(),
        make_snapshot(target_holding_qty=500),
        "SELL", "000001", 1000, 10.0,
    )
    assert not result.passed
    assert result.reason_code == RC_INSUFFICIENT_HOLDING


def test_max_single_pct_rejects():
    engine = RiskEngine()
    rule = make_rule(max_single_pct=0.3)
    snap = make_snapshot(cash=1_000_000, total_market_value=0)
    result = engine.pre_trade_check(rule, snap, "BUY", "000001", 40_000, 10.0)
    assert not result.passed
    assert result.reason_code == RC_MAX_SINGLE


def test_daily_trade_limit_rejects():
    engine = RiskEngine()
    rule = make_rule(max_daily_trades=5)
    snap = make_snapshot(today_trade_count=5)
    result = engine.pre_trade_check(rule, snap, "BUY", "000001", 100, 10.0)
    assert not result.passed
    assert result.reason_code == RC_DAILY_LIMIT
