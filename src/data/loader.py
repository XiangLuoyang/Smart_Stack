from typing import List, Tuple, Optional
import pandas as pd
import yfinance as yf
import streamlit as st
from datetime import datetime, timedelta
from ..config.settings import DataConfig
from src.models.technical import TechnicalIndicators

class StockDataLoader:
    """股票数据加载类"""
    
    def __init__(self):
        self.data_path = 'data/sz100_stocks.csv'
        
    def get_sz100_tickers(self) -> List[str]:
        """获取深证100指数成分股列表"""
        try:
            df = pd.read_csv(self.data_path)
            if 'code' not in df.columns:
                raise ValueError("股票代码列 'code' 不存在")
            return sorted(df['code'].unique().tolist())
        except Exception as e:
            st.error(f"读取深圳100股票列表失败: {str(e)}")
            return []

    def load_stock_data(self, stock_code: str) -> Tuple[pd.DataFrame, str]:
        """加载股票数据"""
        try:
            # 从Yahoo Finance获取数据
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)  # 获取一年数据
            
            ticker = yf.Ticker(stock_code)
            df = ticker.history(start=start_date, end=end_date)
            
            if df.empty:
                st.warning(f"未找到股票 {stock_code} 的数据")
                return pd.DataFrame(), stock_code
                
            # 重置索引，将Date作为列
            df = df.reset_index()
            
            # 确保必要的列存在
            required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df.columns for col in required_columns):
                raise ValueError("数据缺少必要的列")
                
            # 计算技术指标
            ti = TechnicalIndicators()
            df['MA5'] = ti.calculate_ma(df, 5)
            df['MA20'] = ti.calculate_ma(df, 20)
            df['MA50'] = ti.calculate_ma(df, 50)
            df['MA60'] = ti.calculate_ma(df, 60)
            df['RSI'] = ti.calculate_rsi(df)
            macd, signal, hist = ti.calculate_macd(df)
            df['MACD'] = macd
            df['Signal'] = signal
            df['MACD_hist'] = hist
            
            # 填充缺失值
            df = df.fillna(method='ffill').fillna(method='bfill')
            
            return df, stock_code
            
        except Exception as e:
            st.error(f"加载股票数据失败: {str(e)}")
            return pd.DataFrame(), stock_code

    @staticmethod
    def validate_stock_code(stock_code: str) -> bool:
        """验证股票代码格式"""
        if not stock_code:
            return False
        return (stock_code.endswith('.SZ') and 
                stock_code[:-3].isdigit() and 
                len(stock_code[:-3]) == 6)
