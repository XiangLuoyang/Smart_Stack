"""撮合引擎测试。"""
from __future__ import annotations

from datetime import datetime

from app.engine.matching import MatchingEngine, Quote
from app.models.order import Order


def make_order(side="BUY", order_type="MARKET", qty=100, price=None) -> Order:
    return Order(
        account_id="acc1", symbol="000001", side=side,
        order_type=order_type, qty=qty, price=price,
    )


def test_market_order_fills_immediately():
    engine = MatchingEngine()
    order = make_order("BUY", "MARKET", 100)
    quote = Quote(symbol="000001", price=10.0, ts=datetime.now())
    result = engine.match(order, quote)
    assert result.filled
    assert result.fill_price == 10.0
    assert result.fill_qty == 100


def test_market_order_without_quote_rejected():
    engine = MatchingEngine()
    order = make_order("BUY", "MARKET", 100)
    result = engine.match(order, None)
    assert not result.filled


def test_limit_buy_fills_when_price_at_or_below():
    engine = MatchingEngine()
    order = make_order("BUY", "LIMIT", 100, price=10.5)
    quote = Quote(symbol="000001", price=10.0, ts=datetime.now())
    result = engine.match(order, quote)
    assert result.filled
    # A 股规则:限价单按委托价成交(你挂的买单愿意付的最高价)
    assert result.fill_price == 10.5


def test_limit_buy_pending_when_price_above():
    engine = MatchingEngine()
    order = make_order("BUY", "LIMIT", 100, price=9.5)
    quote = Quote(symbol="000001", price=10.0, ts=datetime.now())
    result = engine.match(order, quote)
    assert not result.filled
    assert "未触及" in (result.reason or "")


def test_limit_sell_fills_when_price_at_or_above():
    engine = MatchingEngine()
    order = make_order("SELL", "LIMIT", 100, price=9.5)
    quote = Quote(symbol="000001", price=10.0, ts=datetime.now())
    result = engine.match(order, quote)
    assert result.filled
    assert result.fill_price == 9.5


def test_limit_sell_pending_when_price_below():
    engine = MatchingEngine()
    order = make_order("SELL", "LIMIT", 100, price=10.5)
    quote = Quote(symbol="000001", price=10.0, ts=datetime.now())
    result = engine.match(order, quote)
    assert not result.filled
