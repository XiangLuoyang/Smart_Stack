"""A股纸面交易执行规则(纯函数)。

规则:
- 板块涨跌停:主板 10%,创业板(300)/科创板(688) 20%,ST 5%
- 买入必须为 100 股整数倍(手)
- 卖出允许零股但仅限清仓
- 停牌/缺失昨收/过期行情拒绝
- 价格超出涨跌停拒绝
- 非正价格/数量拒绝
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


QUOTE_MAX_AGE = timedelta(seconds=30)
BOARD_LOT = 100


@dataclass(frozen=True)
class InstrumentState:
    symbol: str
    prev_close: float
    is_st: bool = False
    suspended: bool = False
    quote_ts: Optional[datetime] = None
    newly_listed: bool = False


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: str  # BUY / SELL
    qty: int
    price: Optional[float] = None  # None = market order
    order_type: str = "MARKET"


@dataclass(frozen=True)
class RuleDecision:
    allowed: bool
    code: str
    message: str
    lower_limit: Optional[float] = None
    upper_limit: Optional[float] = None


def _board_limit_pct(symbol: str, is_st: bool) -> float:
    if is_st:
        return 0.05
    code = symbol.split(".")[0]
    if code.startswith("300") or code.startswith("688"):
        return 0.20
    return 0.10


def price_limits(state: InstrumentState) -> tuple[float, float]:
    pct = _board_limit_pct(state.symbol, state.is_st)
    lower = round(state.prev_close * (1 - pct), 2)
    upper = round(state.prev_close * (1 + pct), 2)
    return lower, upper


def validate_order_rules(
    intent: OrderIntent,
    state: InstrumentState,
    now: datetime,
    sellable_qty: int = 0,
) -> RuleDecision:
    if state.suspended:
        return RuleDecision(False, "SUSPENDED", f"{state.symbol} is suspended")

    if state.newly_listed:
        return RuleDecision(False, "NEWLY_LISTED", "newly listed instruments not supported")

    if state.prev_close <= 0:
        return RuleDecision(False, "NO_PREV_CLOSE", "missing or invalid previous close")

    if intent.qty <= 0:
        return RuleDecision(False, "INVALID_QTY", "quantity must be positive")

    if intent.order_type == "LIMIT" and (intent.price is None or intent.price <= 0):
        return RuleDecision(False, "INVALID_PRICE", "limit order requires positive price")

    if intent.side == "BUY" and intent.qty % BOARD_LOT != 0:
        return RuleDecision(False, "INVALID_BOARD_LOT", f"buy qty must be multiple of {BOARD_LOT}")

    if intent.side == "SELL":
        if intent.qty > sellable_qty:
            return RuleDecision(False, "INSUFFICIENT_SHARES", f"sellable {sellable_qty}, requested {intent.qty}")
        if intent.qty % BOARD_LOT != 0 and intent.qty != sellable_qty:
            return RuleDecision(False, "ODD_LOT_NOT_CLOSING", "odd-lot sell only for full position close")

    if state.quote_ts is not None:
        age = now - state.quote_ts
        if age > QUOTE_MAX_AGE:
            return RuleDecision(False, "STALE_QUOTE", f"quote age {age.total_seconds():.0f}s exceeds {QUOTE_MAX_AGE.total_seconds():.0f}s")

    lower, upper = price_limits(state)
    check_price = intent.price if intent.order_type == "LIMIT" else None
    if check_price is not None:
        if check_price < lower or check_price > upper:
            return RuleDecision(
                False, "PRICE_OUT_OF_LIMITS",
                f"price {check_price} outside [{lower}, {upper}]",
                lower_limit=lower, upper_limit=upper,
            )

    return RuleDecision(True, "OK", "order valid", lower_limit=lower, upper_limit=upper)