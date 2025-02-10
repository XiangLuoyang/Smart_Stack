import pandas as pd
import numpy as np
from typing import Dict
from src.config.settings import ModelConfig
import streamlit as st

class RiskCalculator:
    def __init__(self, model_config: ModelConfig):
        self.model_config = model_config

    def calculate_risk_metrics(self, data: pd.DataFrame) -> Dict[str, float]:
        """计算风险指标"""
        try:
            # 计算日收益率
            returns = data['Close'].pct_change().dropna()
            
            # 计算年化波动率
            volatility = returns.std() * np.sqrt(252) * 100
            
            # 计算最大回撤
            cumulative_returns = (1 + returns).cumprod()
            rolling_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - rolling_max) / rolling_max
            max_drawdown = drawdowns.min() * 100
            
            # 计算夏普比率 (使用配置中的无风险利率)
            risk_free_rate = self.model_config.risk_free_rate
            excess_returns = returns.mean() * 252 - risk_free_rate
            sharpe_ratio = excess_returns / (returns.std() * np.sqrt(252))
            
            return {
                '波动率': volatility,
                '最大回撤': abs(max_drawdown),
                '夏普比率': sharpe_ratio
            }
        except Exception as e:
            st.error(f"计算风险指标时出错: {str(e)}")
            return {
                '波动率': 0.0,
                '最大回撤': 0.0,
                '夏普比率': 0.0
            }
