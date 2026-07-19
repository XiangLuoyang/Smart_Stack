"""风险指标计算(从 src/models/risk.py 迁移,去全局单例)。

纯函数式:输入 OHLCV DataFrame,输出波动率/最大回撤/夏普。
"""
from __future__ import annotations

import logging
from typing import Dict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class RiskMetricsCalculator:
    """与原 src/models/risk.RiskCalculator 行为一致,默认无风险利率 3%。"""

    def __init__(self, risk_free_rate: float = 0.03):
        self.risk_free_rate = risk_free_rate

    def calculate(self, data: pd.DataFrame) -> Dict[str, float]:
        try:
            returns = data["Close"].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252) * 100

            cumulative = (1 + returns).cumprod()
            rolling_max = cumulative.expanding().max()
            drawdowns = (cumulative - rolling_max) / rolling_max
            max_drawdown = drawdowns.min() * 100

            excess = returns.mean() * 252 - self.risk_free_rate
            std_annual = returns.std() * np.sqrt(252)
            sharpe = excess / std_annual if std_annual != 0 else 0.0

            return {
                "波动率": float(volatility),
                "最大回撤": float(abs(max_drawdown)),
                "夏普比率": float(sharpe),
            }
        except Exception as e:
            logger.error(f"计算风险指标失败: {e}")
            return {"波动率": 0.0, "最大回撤": 0.0, "夏普比率": 0.0}
