from typing import List, Tuple, Optional
import pandas as pd
import yfinance as yf
import streamlit as st
from ..config.settings import DataConfig

class StockDataLoader:
    """股票数据加载类"""
    
    @staticmethod
    def get_sz100_tickers() -> List[str]:
        """获取深证100指数成分股列表"""
        try:
            df = pd.read_csv(DataConfig.STOCK_LIST_PATH)
            if 'code' not in df.columns:
                raise ValueError("股票代码列 'code' 不存在")
            
            stock_codes = df['code'].tolist()
            for code in stock_codes:
                if not StockDataLoader.validate_stock_code(code):
                    raise ValueError(f"股票代码格式错误: {code}")
            
            return stock_codes
            
        except Exception as e:
            st.error(f"读取深圳100股票列表失败: {str(e)}")
            return []

    @staticmethod
    def load_stock_data(stock_code: str) -> Tuple[pd.DataFrame, str]:
        """加载股票数据"""
        try:
            stock = yf.Ticker(stock_code)
            data = stock.history(period=DataConfig.DEFAULT_PERIOD)
            
            if data.empty:
                raise ValueError(f"未能获取到股票 {stock_code} 的数据")
            
            data.reset_index(inplace=True)
            data['Date'] = pd.to_datetime(data['Date']).dt.tz_localize(None)
            data = data.sort_values('Date').drop_duplicates(subset=['Date'])
            
            return data, stock_code
            
        except Exception as e:
            st.error(f"加载股票{stock_code}数据失败: {str(e)}")
            return pd.DataFrame(), stock_code

    @staticmethod
    def validate_stock_code(stock_code: str) -> bool:
        """验证股票代码格式"""
        if not stock_code:
            return False
        return (stock_code.endswith('.SZ') and 
                stock_code[:-3].isdigit() and 
                len(stock_code[:-3]) == 6)
