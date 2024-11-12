import pandas as pd
import numpy as np
from typing import Dict
from ..config.settings import AnalysisConfig

class RiskMetrics:
    """风险指标计算类"""
    
    @staticmethod
    def calculate_volatility(data: pd.DataFrame) -> float:
        """计算波动率"""
        returns = data['Close'].pct_change().dropna()
        return returns.std() * np.sqrt(AnalysisConfig.TRADING_DAYS)
    
    @staticmethod
    def calculate_sharpe_ratio(data: pd.DataFrame) -> float:
        """计算夏普比率"""
        returns = data['Close'].pct_change().dropna()
        excess_returns = returns - AnalysisConfig.RISK_FREE_RATE/AnalysisConfig.TRADING_DAYS
        return np.sqrt(AnalysisConfig.TRADING_DAYS) * excess_returns.mean() / returns.std()
    
    @staticmethod
    def calculate_max_drawdown(data: pd.DataFrame) -> float:
        """计算最大回撤"""
        cummax = data['Close'].cummax()
        drawdown = (data['Close'] - cummax) / cummax
        return drawdown.min()
    
    @staticmethod
    def calculate_all_metrics(data: pd.DataFrame) -> Dict[str, float]:
        """计算所有风险指标"""
        return {
            '波动率': RiskMetrics.calculate_volatility(data),
            '夏普比率': RiskMetrics.calculate_sharpe_ratio(data),
            '最大回撤': RiskMetrics.calculate_max_drawdown(data)
        }