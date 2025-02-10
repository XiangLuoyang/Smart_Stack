import pandas as pd
import yfinance as yf
from typing import List, Tuple
from src.config.settings import DataConfig
import streamlit as st

class StockDataLoader:
    def __init__(self, data_config: DataConfig):
        self.data_config = data_config

    def get_sz100_tickers(self) -> List[str]:
        """从本地CSV文件获取深证100指数成分股列表"""
        try:
            # 读取存储股票代码的CSV文件，列名为'code'
            df = pd.read_csv(self.data_config.sz100_stocks_file)
            
            # 将股票代码转换为列表
            tickers = df['code'].tolist()
            valid_tickers = []
            for ticker in tickers:
                if self.validate_stock_code(ticker):
                    valid_tickers.append(ticker)
            return valid_tickers
        except Exception as e:
            st.error(f"读取股票列表失败: {str(e)}")
            return []

    def validate_stock_code(self, stock_code: str) -> bool:
        """
        验证股票代码是否有效，通过尝试从 Yahoo Finance 加载数据。
        """
        try:
            stock = yf.Ticker(stock_code)
            data = stock.history(period="1d") # 尝试获取一天的数据
            return not data.empty
        except Exception:
            return False

    def load_stock_data(self, ticker: str) -> Tuple[pd.DataFrame, str]:
        """使用yfinance加载股票数据"""
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="2y")
            
            if data.empty:
                return pd.DataFrame(), ticker
            
            # 重置索引，将日期变成列
            data.reset_index(inplace=True)
            
            # 使用股票代码作为股票名称
            stock_name = ticker
            
            return data, stock_name
            
        except Exception as e:
            st.error(f"加载数据失败: {str(e)}")
            return pd.DataFrame(), ''
