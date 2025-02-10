import pandas as pd
import streamlit as st

class TechnicalIndicatorCalculator:
    def calculate_ma(self, data: pd.DataFrame, period: int) -> pd.Series:
        """计算移动平均线"""
        return data['Close'].rolling(window=period).mean()

    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算RSI"""
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_macd(self, data: pd.DataFrame) -> tuple:
        """计算MACD"""
        exp1 = data['Close'].ewm(span=12, adjust=False).mean()
        exp2 = data['Close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=9, adjust=False).mean()
        macd_histogram = macd - signal_line
        return macd, signal_line, macd_histogram

    def add_all_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """添加所有技术指标"""
        try:
            calculator = TechnicalIndicatorCalculator()
            data['MA5'] = calculator.calculate_ma(data, 5)
            data['MA20'] = calculator.calculate_ma(data, 20)
            data['MA60'] = calculator.calculate_ma(data, 60)
            data['RSI'] = calculator.calculate_rsi(data)
            macd, signal_line, macd_histogram = calculator.calculate_macd(data)
            data['MACD'] = macd
            data['Signal_Line'] = signal_line
            data['MACD_Histogram'] = macd_histogram
            return data
        except Exception as e:
            st.error(f"计算技术指标时出错: {str(e)}")
            return data
