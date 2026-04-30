import pandas as pd
from typing import List, Tuple
from datetime import datetime, timedelta
import tushare as ts
from src.config.settings import DataConfig
import streamlit as st

class StockDataLoader:
    def __init__(self, data_config: DataConfig):
        self.data_config = data_config
        # 初始化Tushare
        try:
            ts.set_token('5d35cfa04f7c37346fc16dbf860b6e8ea05cb5593ee956fed1d9bbc3')  # 请替换为您的Tushare token
            self.pro = ts.pro_api()
            self._cache = {}
            self._cache_timeout = 300  # 缓存超时时间（秒）
        except Exception as e:
            st.error(f"初始化Tushare API失败: {str(e)}")

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

    def load_stock_data(self, stock_code: str) -> Tuple[pd.DataFrame, str]:
        """使用Tushare加载股票数据"""
        try:
            # 验证股票代码格式
            if not stock_code or not (
                (stock_code.endswith('.SZ') or stock_code.endswith('.SS')) and 
                stock_code[:-3].isdigit() and 
                len(stock_code[:-3]) == 6
            ):
                st.warning(f"股票代码 {stock_code} 格式不正确")
                return pd.DataFrame(), stock_code

            # 检查缓存
            cache_key = f"{stock_code}_{datetime.now().date()}"
            if cache_key in self._cache:
                cache_data, cache_time = self._cache[cache_key]
                if (datetime.now() - cache_time).seconds < self._cache_timeout:
                    st.info("使用缓存数据")
                    return cache_data, stock_code

            # 准备日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)  # 获取一年数据

            # 获取日线数据
            df = self.pro.daily(
                ts_code=stock_code,
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d')
            )

            if df.empty:
                st.error(f"无法获取股票 {stock_code} 的数据")
                return pd.DataFrame(), stock_code

            # 重命名列以匹配原有格式
            df = df.rename(columns={
                'trade_date': 'Date',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'vol': 'Volume'
            })

            # 转换日期格式
            df['Date'] = pd.to_datetime(df['Date'])

            # 按日期升序排序
            df = df.sort_values('Date')

            # 重置索引
            df = df.reset_index(drop=True)

            # 更新缓存
            self._cache[cache_key] = (df, datetime.now())

            st.success(f"成功获取到{stock_code}的历史数据，共{len(df)}条记录")
            return df, stock_code

        except Exception as e:
            st.error(f"加载数据失败: {str(e)}")
            return pd.DataFrame(), ''
