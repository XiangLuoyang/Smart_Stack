import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict
from scipy import stats
import yfinance as yf
import streamlit as st

class ReturnPredictor:
    def calculate_expected_return(
        self,
        ticker: str,
        start_date: datetime,
        days: int,
        confidence: float
    ) -> Dict[str, float]:
        """计算预期收益率和置信区间"""
        try:
            # 获取历史数据
            stock = yf.Ticker(ticker)
            hist_data = stock.history(start=start_date)
            
            if hist_data.empty:
                return {'error': '无法获取历史数据'}
            
            # 计算历史日收益率
            returns = hist_data['Close'].pct_change().dropna()
            
            # 计算预期收益率（年化）
            exp_return = returns.mean() * 252 * 100
            
            # 计算收益率的标准差
            std_dev = returns.std() * np.sqrt(252)
            
            # 计算置信区间
            z_score = stats.norm.ppf((1 + confidence) / 2)
            margin_of_error = z_score * std_dev * 100
            
            return {
                'expected_return': exp_return,
                'lower_bound': exp_return - margin_of_error,
                'upper_bound': exp_return + margin_of_error,
                'forecast': hist_data['Close'].iloc[-days:].values
            }
        except Exception as e:
            return {'error': str(e)}
