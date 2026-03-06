import pandas as pd
from typing import List, Tuple, Optional
from datetime import datetime, timedelta
import yfinance as yf  # 切换到YFinance
import streamlit as st
from src.config.settings import DataConfig
import os

class StockDataLoader:
    def __init__(self, data_config: DataConfig):
        self.data_config = data_config
        self._cache = {}
        self._cache_timeout = 300  # 缓存超时时间（秒）
        
        # YFinance无需API Token初始化
        st.info("数据源已切换到YFinance，支持A股、美股、港股")

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
        """使用YFinance加载股票数据（支持A股、美股、港股）"""
        try:
            # 验证股票代码格式
            if not stock_code:
                st.warning("股票代码不能为空")
                return pd.DataFrame(), ''
            
            # 标准化股票代码格式
            standardized_code = self._standardize_stock_code(stock_code)
            
            # 检查缓存
            cache_key = f"{standardized_code}_{datetime.now().date()}"
            if cache_key in self._cache:
                cache_data, cache_time = self._cache[cache_key]
                if (datetime.now() - cache_time).seconds < self._cache_timeout:
                    st.info(f"使用缓存数据: {standardized_code}")
                    return cache_data, standardized_code

            # 获取股票数据
            st.info(f"正在获取 {standardized_code} 数据...")
            
            # 使用YFinance获取数据
            ticker = yf.Ticker(standardized_code)
            
            # 获取1年历史数据
            df = ticker.history(period="1y")
            
            if df.empty:
                st.error(f"无法获取股票 {standardized_code} 的数据，请检查代码格式")
                # 尝试备用格式
                alt_code = self._try_alternative_format(stock_code)
                if alt_code and alt_code != standardized_code:
                    st.info(f"尝试备用格式: {alt_code}")
                    return self.load_stock_data(alt_code)
                return pd.DataFrame(), standardized_code

            # 标准化数据格式
            df = self._standardize_yfinance_data(df, standardized_code)
            
            # 更新缓存
            self._cache[cache_key] = (df, datetime.now())
            
            st.success(f"成功获取到 {standardized_code} 的历史数据，共{len(df)}条记录")
            return df, standardized_code

        except Exception as e:
            st.error(f"加载数据失败: {str(e)}")
            return pd.DataFrame(), ''

    def _standardize_stock_code(self, stock_code: str) -> str:
        """标准化股票代码格式"""
        # 移除空格和特殊字符
        code = stock_code.strip().upper()
        
        # 如果已经是YFinance格式，直接返回
        if any(code.endswith(suffix) for suffix in ['.SZ', '.SS', '.SH', '.HK', '.']):
            return code
        
        # 根据长度判断市场类型
        if len(code) == 6:
            # A股代码：前2位判断交易所
            if code.startswith(('00', '30')):  # 深交所
                return f"{code}.SZ"
            elif code.startswith(('60', '68')):  # 上交所
                return f"{code}.SS"
            elif code.startswith('90'):  # 科创板
                return f"{code}.SH"
        elif len(code) == 4 or len(code) == 5:
            # 美股代码：直接返回
            return code
        elif len(code) == 5 and code.endswith('.HK'):
            # 港股代码：已经是正确格式
            return code
        
        # 无法识别，返回原格式
        return code

    def _try_alternative_format(self, stock_code: str) -> Optional[str]:
        """尝试备用股票代码格式"""
        code = stock_code.strip().upper()
        
        # 尝试添加.SZ后缀
        if len(code) == 6 and code.startswith(('00', '30')):
            return f"{code}.SZ"
        
        # 尝试添加.SS后缀
        if len(code) == 6 and code.startswith(('60', '68')):
            return f"{code}.SS"
        
        # 尝试添加.SH后缀
        if len(code) == 6 and code.startswith('90'):
            return f"{code}.SH"
        
        return None

    def _standardize_yfinance_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """将YFinance数据转换为项目标准格式"""
        if df.empty:
            return df
        
        # 重置索引，将Date变为列
        df = df.reset_index()
        
        # 重命名列以匹配原有格式
        column_mapping = {
            'Date': 'Date',
            'Open': 'Open',
            'High': 'High',
            'Low': 'Low',
            'Close': 'Close',
            'Volume': 'Volume'
        }
        
        # 只重命名存在的列
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        # 确保Date列是datetime类型
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
        
        # 按日期升序排序
        df = df.sort_values('Date')
        
        # 重置索引
        df = df.reset_index(drop=True)
        
        # 添加股票代码列
        df['symbol'] = stock_code
        
        return df

    def get_market_info(self, stock_code: str) -> dict:
        """获取股票市场信息"""
        try:
            standardized_code = self._standardize_stock_code(stock_code)
            ticker = yf.Ticker(standardized_code)
            info = ticker.info
            
            return {
                'symbol': standardized_code,
                'name': info.get('longName', info.get('shortName', 'N/A')),
                'market': self._detect_market(standardized_code),
                'currency': info.get('currency', 'N/A'),
                'timezone': info.get('exchangeTimezoneName', 'N/A')
            }
        except Exception as e:
            return {
                'symbol': stock_code,
                'error': str(e)
            }

    def _detect_market(self, stock_code: str) -> str:
        """检测股票所属市场"""
        if stock_code.endswith('.SZ'):
            return '深圳证券交易所'
        elif stock_code.endswith('.SS') or stock_code.endswith('.SH'):
            return '上海证券交易所'
        elif stock_code.endswith('.HK'):
            return '香港交易所'
        elif '.' not in stock_code and len(stock_code) <= 5:
            return '纽约证券交易所/NASDAQ'
        else:
            return '未知市场'

    def batch_load_stock_data(self, stock_codes: List[str]) -> List[Tuple[pd.DataFrame, str]]:
        """批量加载多只股票数据"""
        results = []
        total = len(stock_codes)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, code in enumerate(stock_codes):
            status_text.text(f"正在处理 {i+1}/{total}: {code}")
            df, standardized_code = self.load_stock_data(code)
            results.append((df, standardized_code))
            progress_bar.progress((i + 1) / total)
        
        progress_bar.empty()
        status_text.empty()
        
        return results
