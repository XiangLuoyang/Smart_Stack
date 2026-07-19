"""订单服务集成测试:风控 + 撮合 + 费用 + 持仓 + 资金 一致性。"""
from __future__ import annotations

from datetime import datetime

from app.engine.matching import Quote
from app.models.account import Account
from app.models.order import ORDER_STATUS_FILLED, ORDER_STATUS_PENDING, ORDER_STATUS_REJECTED
from app.services.account_service import AccountService
from app.services.order_service import OrderService


def _seed_account(db_session, cash=1_000_000.0) -> Account:
    return AccountService(db_session).create_account("test", initial_cash=cash)


def test_market_buy_fills_and_updates_cash_position(db_session):
    account = _seed_account(db_session)
    svc = OrderService(db_session)
    quote = Quote(symbol="000001", price=10.0, ts=datetime.now())

    result = svc.place(
        account.id, "000001", "BUY", 1000, "MARKET", quote=quote,
    )
    assert result.accepted
    assert result.order.status == ORDER_STATUS_FILLED
    assert result.trade is not None

    db_session.refresh(account)
    # 现金 = 100万 - (10000 本金 + 5 佣金) = 999995
    assert account.cash == 1_000_000 - 10_000 - 5.0
    # 持仓 1000 股,均价 10
    pos = svc.position_svc.get(account.id, "000001")
    assert pos.qty == 1000
    assert pos.avg_cost == 10.0


def test_limit_order_pending_until_price_hits(db_session):
    account = _seed_account(db_session)
    svc = OrderService(db_session)
    # 委托 9.5 买,市价 10 → 挂起
    result = svc.place(
        account.id, "000001", "BUY", 1000, "LIMIT", price=9.5,
        quote=Quote(symbol="000001", price=10.0, ts=datetime.now()),
    )
    assert result.accepted
    assert result.order.status == ORDER_STATUS_PENDING
    assert result.trade is None

    # 价格跌到 9.0,巡检触发成交
    filled = svc.scan_pending_orders(
        {"000001": Quote(symbol="000001", price=9.0, ts=datetime.now())}
    )
    assert filled == 1

    db_session.refresh(account)
    # 成交后现金扣减:1000 * 9.5 + 5 佣金 = 9505
    assert account.cash == 1_000_000 - 9_505.0


def test_sell_rejected_insufficient_holding(db_session):
    account = _seed_account(db_session)
    svc = OrderService(db_session)
    result = svc.place(
        account.id, "000001", "SELL", 1000, "MARKET",
        quote=Quote(symbol="000001", price=10.0, ts=datetime.now()),
    )
    assert not result.accepted
    assert result.order.status == ORDER_STATUS_REJECTED


def test_complete_buy_then_sell_cycle(db_session):
    """买入 → 持仓 → 卖出 → 持仓清零 全流程。"""
    account = _seed_account(db_session)
    svc = OrderService(db_session)
    q = Quote(symbol="000001", price=10.0, ts=datetime.now())

    svc.place(account.id, "000001", "BUY", 1000, "MARKET", quote=q)
    db_session.refresh(account)
    cash_after_buy = account.cash
    assert cash_after_buy < 1_000_000

    svc.place(account.id, "000001", "SELL", 1000, "MARKET", quote=q)
    db_session.refresh(account)
    # 卖出后:无持仓,现金 = cash_after_buy + (10000 - 5 佣金 - 10 印花税) = cash_after_buy + 9985
    assert abs(account.cash - (cash_after_buy + 9985.0)) < 1e-6
    assert svc.position_svc.get(account.id, "000001") is None


def test_cancel_pending_order(db_session):
    account = _seed_account(db_session)
    svc = OrderService(db_session)
    result = svc.place(
        account.id, "000001", "BUY", 1000, "LIMIT", price=9.0,
        quote=Quote(symbol="000001", price=10.0, ts=datetime.now()),
    )
    ok, msg = svc.cancel(result.order.id)
    assert ok
    db_session.refresh(result.order)
    assert result.order.status == "CANCELLED"
