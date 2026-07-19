"""风控引擎:下单前拦截。

五条核心规则:
    1. 单票仓位上限(max_single_pct):本笔买入后,该标的市值占总资产比例不超上限
    2. 总仓位上限(max_position_pct):本笔买入后,持仓总市值占总资产比例不超上限
    3. 单笔最大金额:防御性,本笔买入金额不超过账户总资产
    4. 日内交易次数:max_daily_trades
    5. 持仓不足卖出:卖出数量不超过现有持仓

纯函数式:输入(规则 + 账户快照 + 订单 + 最新价),输出校验结果。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from typing import Optional

from app.models.order import ORDER_SIDE_BUY
from app.models.risk_rule import RiskRule


@dataclass(frozen=True)
class AccountSnapshot:
    """风控需要的账户当前快照(由 services 层组装传入)。"""

    cash: float
    total_market_value: float  # 现有持仓市值
    target_holding_value: float  # 目标标的现有持仓市值
    target_holding_qty: float  # 目标标的现有持仓数量
    today_trade_count: int  # 今日已成交笔数

    @property
    def total_assets(self) -> float:
        return self.cash + self.total_market_value


@dataclass(frozen=True)
class RiskCheckResult:
    passed: bool
    reason_code: Optional[str] = None  # 不通过时的规则码
    message: str = ""


# 规则码
RC_MAX_SINGLE = "MAX_SINGLE_PCT"
RC_MAX_POSITION = "MAX_POSITION_PCT"
RC_OVER_BUDGET = "OVER_BUDGET"
RC_DAILY_LIMIT = "DAILY_TRADE_LIMIT"
RC_INSUFFICIENT_HOLDING = "INSUFFICIENT_HOLDING"


class RiskEngine:
    """pre_trade_check 在撮合前调用,任一不通过即拒绝。"""

    def pre_trade_check(
        self,
        rule: RiskRule,
        snapshot: AccountSnapshot,
        side: str,
        symbol: str,
        qty: float,
        price: float,
        now: datetime | None = None,
    ) -> RiskCheckResult:
        now = now or datetime.now()
        amount = qty * price

        # 规则 5:卖出必须有足够持仓
        if side != ORDER_SIDE_BUY:
            if qty > snapshot.target_holding_qty + 1e-9:
                return RiskCheckResult(
                    False, RC_INSUFFICIENT_HOLDING,
                    f"卖出 {qty} 超过现有持仓 {snapshot.target_holding_qty}",
                )
            return RiskCheckResult(True)

        # 下面都是买入校验
        total_assets = snapshot.total_assets

        # 规则 3:本笔金额不超过总资产(防御性,避免单笔爆仓)
        if amount > total_assets + 1e-6:
            return RiskCheckResult(
                False, RC_OVER_BUDGET,
                f"买入金额 {amount:.2f} 超过总资产 {total_assets:.2f}",
            )

        # 规则 1:单票仓位上限
        new_target_value = snapshot.target_holding_value + amount
        if total_assets > 0 and new_target_value / total_assets > rule.max_single_pct + 1e-9:
            return RiskCheckResult(
                False, RC_MAX_SINGLE,
                f"单票仓位 {new_target_value / total_assets:.1%} 超过上限 {rule.max_single_pct:.1%}",
            )

        # 规则 2:总仓位上限
        new_total_market_value = snapshot.total_market_value + amount
        if total_assets > 0 and new_total_market_value / total_assets > rule.max_position_pct + 1e-9:
            return RiskCheckResult(
                False, RC_MAX_POSITION,
                f"总仓位 {new_total_market_value / total_assets:.1%} 超过上限 {rule.max_position_pct:.1%}",
            )

        # 规则 4:日内交易次数
        if snapshot.today_trade_count >= rule.max_daily_trades:
            return RiskCheckResult(
                False, RC_DAILY_LIMIT,
                f"今日已成交 {snapshot.today_trade_count} 笔,达到上限 {rule.max_daily_trades}",
            )

        return RiskCheckResult(True)
