import pandas as pd
import numpy as np
from datetime import datetime
import typing
from typing import Dict
from scipy import stats
import yfinance as yf
import streamlit as st
from src.models.technical import TechnicalIndicatorCalculator

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
            # 获取历史数据 (缩短历史数据时间跨度为 1 年，以加快加载速度, 移除 start_date 参数)
            stock = yf.Ticker(ticker)
            hist_data = stock.history(period="1y")
            
            if hist_data.empty:
                return {'error': '无法获取历史数据'}
            
            # 打印 hist_data 查看原始数据
            print(f"Ticker: {ticker} - Hist Data:\n{hist_data}")

            # 计算历史日收益率
            returns = hist_data['Close'].pct_change().dropna()
            
            # 检查 returns 是否为空
            if returns.empty:
                print(f"Ticker: {ticker} - Returns Series is empty.")
                exp_return = np.nan # 直接赋值为 NaN
            else:
                # 计算预期收益率（年化）
                exp_return = returns.mean() * 252 * 100
            
            # 计算收益率的标准差
            std_dev = returns.std() * np.sqrt(252)
            
            # 计算置信区间
            z_score = stats.norm.ppf((1 + confidence) / 2)
            margin_of_error = z_score * std_dev * 100
            
            # 计算技术指标
            indicator_calculator = TechnicalIndicatorCalculator()
            data_with_indicators = indicator_calculator.add_all_indicators(hist_data.copy()) # 避免修改原始数据

            # 初始化技术指标平均值，防止 NameError
            ma5_avg = np.nan
            ma20_avg = np.nan
            rsi_avg = np.nan
            macd_avg = np.nan


            # 计算技术指标的平均值 (简化处理，实际应用中可以更精细地分析)
            ma5_avg = data_with_indicators['MA5'].mean() if not data_with_indicators['MA5'].empty else np.nan
            ma20_avg = data_with_indicators['MA20'].mean() if not data_with_indicators['MA20'].empty else np.nan
            rsi_avg = data_with_indicators['RSI'].mean() if not data_with_indicators['RSI'].empty else np.nan # RSI 中性值
            macd_avg = data_with_indicators['MACD'].mean() if not data_with_indicators['MACD'].empty else np.nan

            # 检查数据和技术指标计算结果
            print(f"Ticker: {ticker}")
            print(f"Hist Data Empty: {hist_data.empty}")
            print(f"Returns: {returns}")
            print(f"Exp Return: {exp_return}")
            print(f"MA5 Avg: {ma5_avg}")
            print(f"MA20 Avg: {ma20_avg}")
            print(f"RSI Avg: {rsi_avg}")
            print(f"MACD Avg: {macd_avg}")

            # 综合指标权重 (这里权重可以根据实际情况调整)
            weights = {
                'history_return': 0.5,
                'ma5': 0.1,
                'ma20': 0.1,
                'rsi': 0.15,
                'macd': 0.15,
            }

            # 加权平均计算综合预期收益率
            composite_exp_return = np.nanmean([ # 使用 np.nanmean 忽略 NaN 值
                exp_return * weights['history_return'],
                ma5_avg * weights['ma5'],
                ma20_avg * weights['ma20'],
                (rsi_avg - 50) * weights['rsi'], # RSI 偏离中性值程度
                macd_avg * weights['macd']
            ])


            return {
                'expected_return': composite_exp_return, # 使用综合预期收益率
                'lower_bound': exp_return - margin_of_error, # 置信区间仍基于历史收益率
                'upper_bound': exp_return + margin_of_error,
                'forecast': hist_data['Close'].iloc[-days:].values
            }
        except Exception as e:
            return {'error': str(e)}

    def get_top_stock_recommendations(self, tickers: typing.List[str], start_date: datetime, days: int, confidence: float) -> typing.List[typing.Tuple[str, float]]:
        """
        计算多个股票的预期收益率，并返回 TOP 10 推荐股票。

        Args:
            tickers: 股票代码列表。
            start_date: 历史数据起始日期。
            days: 预测天数。
            confidence: 置信区间。

        Returns:
            包含 TOP 10 股票代码和预期收益率的列表，按预期收益率降序排列。
        """
        stock_returns = []
        for ticker in tickers:
            prediction_results = self.calculate_expected_return(ticker, start_date, days, confidence)
            if 'error' not in prediction_results:
                stock_returns.append((ticker, prediction_results['expected_return']))

        # 按预期收益率降序排序
        stock_returns.sort(key=lambda item: item[1], reverse=True)

        return stock_returns[:10]  # 返回 TOP 10 股票
