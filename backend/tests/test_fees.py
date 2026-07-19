"""费用计算器测试。"""
from __future__ import annotations

from app.core.config import FeesConfig
from app.engine.fees import FeesCalculator


def make():
    return FeesCalculator(FeesConfig())  # 用默认配置,不受 .env 影响


def test_commission_min_threshold():
    """金额过小时,佣金取最低 5 元。"""
    f = make()
    # 100 股 * 3 元 = 300 元 * 0.00025 = 0.075 元,远低于最低 5 元
    fee = f.calc("BUY", "000001", 3.0, 100)
    assert fee.commission == 5.0
    assert fee.stamp_duty == 0.0  # 买入无印花税
    assert fee.transfer_fee == 0.0  # 深市无过户费


def test_commission_above_min():
    """大额交易佣金按比例。"""
    f = make()
    # 1万股 * 10 元 = 10万 * 0.00025 = 25 元
    fee = f.calc("BUY", "000001", 10.0, 10_000)
    assert fee.commission == 25.0


def test_stamp_duty_only_on_sell():
    """印花税仅卖出方。"""
    f = make()
    buy_fee = f.calc("BUY", "000001", 10.0, 10_000)
    sell_fee = f.calc("SELL", "000001", 10.0, 10_000)
    assert buy_fee.stamp_duty == 0.0
    assert sell_fee.stamp_duty == 100.0  # 10万 * 0.001


def test_transfer_fee_only_shanghai():
    """过户费仅沪市(代码 6 开头)。默认费率 0.00002 → 10万 * 0.00002 = 2 元。"""
    f = make()
    sz = f.calc("BUY", "000001", 10.0, 10_000)
    sh = f.calc("BUY", "600000", 10.0, 10_000)
    assert sz.transfer_fee == 0.0
    assert sh.transfer_fee == 2.0  # 10万 * 0.00002 = 2


def test_signed_total_buy_sell():
    """带符号的现金影响:买入为正,卖出为负。"""
    f = make()
    # 1000 股 * 10 元 = 1万;佣金 max(2.5, 5) = 5;无印花税;深市无过户费
    buy_total = f.signed_total("BUY", "000001", 10.0, 1000)
    assert buy_total == 10_000 + 5.0  # 10005

    sell_total = f.signed_total("SELL", "000001", 10.0, 1000)
    # 卖出:本金 - 佣金 5 - 印花税 10
    assert sell_total == 10_000 - 5.0 - 10.0  # 9985


def test_zero_qty():
    """零股保护:全部为 0。"""
    f = make()
    fee = f.calc("BUY", "000001", 10.0, 0)
    assert fee.commission == 0.0
    assert fee.stamp_duty == 0.0
    assert fee.transfer_fee == 0.0
