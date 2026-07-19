"""回测引擎测试:用合成 K 线,验证净值/指标计算正确。"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from app.services.backtest_service import BacktestService, _metrics_from_curve


def _make_df(prices: list[float], start: str = "2025-01-01") -> pd.DataFrame:
    dates = pd.date_range(start, periods=len(prices), freq="D")
    return pd.DataFrame({
        "Date": dates,
        "Open": prices,
        "High": [p * 1.01 for p in prices],
        "Low": [p * 0.99 for p in prices],
        "Close": prices,
        "Volume": [10_000] * len(prices),
    })


def test_metrics_empty_curve():
    """空净值曲线 → 所有指标为 0。"""
    m = _metrics_from_curve([], [])
    assert m["total_return"] == 0.0
    assert m["sharpe"] == 0.0
    assert m["trade_count"] == 0


def test_flat_curve_zero_return():
    """净值恒为 1 → 收益 0、夏普 0。"""
    curve = [{"ts": f"2025-01-{i:02d}T00:00:00", "nv": 1.0} for i in range(1, 11)]
    m = _metrics_from_curve(curve, [])
    assert m["total_return"] == 0.0
    assert m["sharpe"] == 0.0
    assert m["max_drawdown"] == 0.0


def test_ma_cross_generates_trades_on_trend(db_session):
    """单调上涨的合成数据:双均线策略应产生交易且净值增长。"""
    # 30 天,价格从 10 涨到 20
    prices = [10 + i * 0.4 for i in range(30)]
    df = _make_df(prices)
    svc = BacktestService(db_session)
    run = svc.run(
        symbol="TEST",
        strategy_name="ma_cross",
        params={"fast": 3, "slow": 10},
        df=df,
        start=datetime(2025, 1, 1),
        end=datetime(2025, 12, 31),
        initial_cash=1_000_000,
    )
    import json
    m = json.loads(run.metrics_json)
    # 单调上涨,最终应盈利
    assert m["total_return"] > 0
    assert m["trade_count"] >= 1
    # 净值曲线非空
    curve = json.loads(run.equity_curve_json)
    assert len(curve) > 0
    assert curve[-1]["nv"] > 1.0
