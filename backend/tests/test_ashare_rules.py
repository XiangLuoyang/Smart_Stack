"""A股执行规则测试。"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.engine.ashare_rules import (
    InstrumentState,
    OrderIntent,
    RuleDecision,
    price_limits,
    validate_order_rules,
)

NOW = datetime(2026, 7, 22, 10, 0, 0)


def normal_state(**kwargs) -> InstrumentState:
    defaults = dict(symbol="600000", prev_close=10.0, quote_ts=NOW - timedelta(seconds=5))
    defaults.update(kwargs)
    return InstrumentState(**defaults)


def intent(**kwargs) -> OrderIntent:
    defaults = dict(symbol="600000", side="BUY", qty=100, order_type="MARKET")
    defaults.update(kwargs)
    return OrderIntent(**defaults)


class TestPriceLimits:
    @pytest.mark.parametrize("symbol,limit_pct", [
        ("600000", 0.10),
        ("000001", 0.10),
        ("300001", 0.20),
        ("688001", 0.20),
    ])
    def test_board_price_limits(self, symbol, limit_pct):
        state = InstrumentState(symbol=symbol, prev_close=10.0, quote_ts=NOW)
        lower, upper = price_limits(state)
        assert lower == round(10 * (1 - limit_pct), 2)
        assert upper == round(10 * (1 + limit_pct), 2)

    def test_st_5pct_limit(self):
        state = InstrumentState(symbol="600000", prev_close=10.0, is_st=True, quote_ts=NOW)
        lower, upper = price_limits(state)
        assert lower == 9.50
        assert upper == 10.50


class TestOrderValidation:
    def test_valid_buy(self):
        d = validate_order_rules(intent(), normal_state(), NOW)
        assert d.allowed is True
        assert d.code == "OK"

    def test_buy_requires_board_lot(self):
        d = validate_order_rules(intent(qty=150), normal_state(), NOW)
        assert d.allowed is False
        assert d.code == "INVALID_BOARD_LOT"

    def test_stale_quote_rejected(self):
        state = normal_state(quote_ts=NOW - timedelta(seconds=31))
        d = validate_order_rules(intent(), state, NOW)
        assert d.allowed is False
        assert d.code == "STALE_QUOTE"

    def test_suspended_rejected(self):
        d = validate_order_rules(intent(), normal_state(suspended=True), NOW)
        assert d.allowed is False
        assert d.code == "SUSPENDED"

    def test_newly_listed_rejected(self):
        d = validate_order_rules(intent(), normal_state(newly_listed=True), NOW)
        assert d.allowed is False
        assert d.code == "NEWLY_LISTED"

    def test_price_out_of_limits(self):
        d = validate_order_rules(
            intent(order_type="LIMIT", price=11.5),
            normal_state(),
            NOW,
        )
        assert d.allowed is False
        assert d.code == "PRICE_OUT_OF_LIMITS"
        assert d.lower_limit == 9.0
        assert d.upper_limit == 11.0

    def test_sell_insufficient_shares(self):
        d = validate_order_rules(
            intent(side="SELL", qty=200),
            normal_state(),
            NOW,
            sellable_qty=100,
        )
        assert d.allowed is False
        assert d.code == "INSUFFICIENT_SHARES"

    def test_odd_lot_sell_closing_allowed(self):
        d = validate_order_rules(
            intent(side="SELL", qty=50),
            normal_state(),
            NOW,
            sellable_qty=50,
        )
        assert d.allowed is True

    def test_odd_lot_sell_not_closing_rejected(self):
        d = validate_order_rules(
            intent(side="SELL", qty=50),
            normal_state(),
            NOW,
            sellable_qty=200,
        )
        assert d.allowed is False
        assert d.code == "ODD_LOT_NOT_CLOSING"

    def test_nonpositive_qty_rejected(self):
        d = validate_order_rules(intent(qty=0), normal_state(), NOW)
        assert d.allowed is False
        assert d.code == "INVALID_QTY"

    def test_limit_without_price_rejected(self):
        d = validate_order_rules(intent(order_type="LIMIT", price=None), normal_state(), NOW)
        assert d.allowed is False
        assert d.code == "INVALID_PRICE"

    def test_no_prev_close_rejected(self):
        d = validate_order_rules(intent(), normal_state(prev_close=0), NOW)
        assert d.allowed is False
        assert d.code == "NO_PREV_CLOSE"