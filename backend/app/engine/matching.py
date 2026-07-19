"""纸面撮合引擎。

设计原则:
- 纯函数式,输入(订单 + 行情)输出(成交流水),不直接操作数据库
- 市价单(MARKET)即时按最新价成交
- 限价单(LIMIT):买入价 >= 最新价 或 卖出价 <= 最新价 时触发成交
- 纸面撮合不做部分成交,一单一笔
- 资金 / 持仓的扣减由 services 层在调用 match() 后统一提交
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.models.order import (
    ORDER_SIDE_BUY,
    ORDER_SIDE_SELL,
    ORDER_TYPE_LIMIT,
    ORDER_TYPE_MARKET,
    Order,
)


@dataclass(frozen=True)
class Quote:
    """最新行情快照。"""

    symbol: str
    price: float
    ts: datetime
    bid: Optional[float] = None  # 买一(可选,用于限价撮合)
    ask: Optional[float] = None  # 卖一


@dataclass(frozen=True)
class MatchResult:
    """撮合结果。"""

    filled: bool
    fill_price: Optional[float] = None
    fill_qty: Optional[float] = None
    reason: Optional[str] = None  # 未成交原因

    @classmethod
    def filled_at(cls, price: float, qty: float) -> "MatchResult":
        return cls(filled=True, fill_price=price, fill_qty=qty)

    @classmethod
    def pending(cls, reason: str = "限价单未触及") -> "MatchResult":
        return cls(filled=False, reason=reason)


class MatchingEngine:
    """撮合规则:市价即时成交,限价按价格触及判定。"""

    def match(self, order: Order, quote: Optional[Quote]) -> MatchResult:
        # 无行情:市价单拒绝,限价单挂起
        if quote is None:
            if order.order_type == ORDER_TYPE_MARKET:
                return MatchResult(filled=False, reason="市价单缺少行情")
            return MatchResult.pending()

        if order.order_type == ORDER_TYPE_MARKET:
            return MatchResult.filled_at(quote.price, order.qty)

        if order.order_type == ORDER_TYPE_LIMIT:
            if order.price is None:
                return MatchResult(filled=False, reason="限价单缺少价格")
            # A 股规则:限价单按委托价成交(你挂的价格),触发判定用市价
            if order.side == ORDER_SIDE_BUY and order.price >= quote.price:
                return MatchResult.filled_at(order.price, order.qty)
            if order.side == ORDER_SIDE_SELL and order.price <= quote.price:
                return MatchResult.filled_at(order.price, order.qty)
            return MatchResult.pending()

        return MatchResult(filled=False, reason=f"未知订单类型 {order.order_type}")
