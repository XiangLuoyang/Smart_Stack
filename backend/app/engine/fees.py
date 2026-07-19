"""A 股交易费用计算器。

默认费率(可经 FeesConfig / 环境变量覆盖):
    佣金: 万分之 2.5,最低 5 元
    印花税: 千分之 1,仅卖出方
    过户费: 千分之 0.2,沪市双边(代码以 6 开头视为沪市)

纯函数,无副作用,易测试。
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.config import FeesConfig, get_settings
from app.models.order import ORDER_SIDE_BUY


def _is_shanghai(symbol: str) -> bool:
    """沪市判定:A 股代码以 6 开头(600/601/603/605/688),或带 .SS 后缀。"""
    code = symbol.upper().split(".")[0]
    return code.startswith("6") or symbol.upper().endswith(".SS")


@dataclass(frozen=True)
class FeeBreakdown:
    """单笔成交费用明细。"""

    commission: float
    stamp_duty: float
    transfer_fee: float

    @property
    def total(self) -> float:
        return self.commission + self.stamp_duty + self.transfer_fee


class FeesCalculator:
    """根据成交金额与方向计算费用。"""

    def __init__(self, config: FeesConfig | None = None):
        self.config = config or get_settings().fees

    def calc(self, side: str, symbol: str, price: float, qty: float) -> FeeBreakdown:
        amount = price * qty
        amount = price * qty
        if amount <= 0:
            return FeeBreakdown(commission=0.0, stamp_duty=0.0, transfer_fee=0.0)
        # 佣金:双边,有最低收取
        commission = max(amount * self.config.commission_rate, self.config.commission_min)
        # 印花税:仅卖出
        stamp_duty = amount * self.config.stamp_duty_rate if side == "SELL" else 0.0
        # 过户费:仅沪市双边
        transfer_fee = amount * self.config.transfer_fee_rate if _is_shanghai(symbol) else 0.0
        return FeeBreakdown(
            commission=round(commission, 4),
            stamp_duty=round(stamp_duty, 4),
            transfer_fee=round(transfer_fee, 4),
        )

    def cash_delta(self, side: str, symbol: str, price: float, qty: float) -> float:
        """现金变化量(直接 += 到 account.cash)。

        买入:负数(现金减少 = 本金 + 全部费用)
        卖出:正数(现金增加 = 本金 - 全部费用)
        """
        breakdown = self.calc(side, symbol, price, qty)
        principal = price * qty
        if side == ORDER_SIDE_BUY:
            return round(-(principal + breakdown.total), 4)
        return round(principal - breakdown.total, 4)

    # 向后兼容(测试用):保留旧名,返回绝对值
    def signed_total(self, side: str, symbol: str, price: float, qty: float) -> float:
        """已废弃,改用 cash_delta。返回买入支出/卖出收入的绝对值。"""
        return abs(self.cash_delta(side, symbol, price, qty))
