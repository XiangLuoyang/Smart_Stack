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
            return tickers
        except Exception as e:
            st.error(f"读取股票列表失败: {str(e)}")
            return []

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
