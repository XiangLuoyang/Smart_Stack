import pandas as pd
from typing import List, Tuple, Optional
from datetime import datetime, timedelta
import streamlit as st
from src.config.settings import DataConfig
import os

# 导入智能数据源
from .smart_loader import get_smart_loader

class StockDataLoader:
    def __init__(self, data_config: DataConfig):
        self.data_config = data_config
        self._cache = {}
        self._cache_timeout = 300  # 缓存超时时间（秒）
        
        # 使用智能数据源
        self.smart_loader = get_smart_loader(data_config)
        st.info("📊 使用智能数据源 - 自动选择最佳数据源")

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

    def load_stock_data(self, stock_code: str, period: str = "daily",
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> Tuple[pd.DataFrame, str]:
        """
        智能加载股票数据（支持多数据源自动切换）
        
        Args:
            stock_code: 股票代码
            period: 数据周期 (daily, weekly, monthly)
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            
        Returns:
            (DataFrame, 标准化代码)
        """
        try:
            # 验证股票代码格式
            if not stock_code:
                st.warning("股票代码不能为空")
                return pd.DataFrame(), ''
            
            # 检查缓存
            cache_key = f"{stock_code}_{period}_{start_date}_{end_date}"
            if cache_key in self._cache:
                cache_data, cache_time = self._cache[cache_key]
                if (datetime.now() - cache_time).seconds < self._cache_timeout:
                    st.info(f"📦 使用缓存数据: {stock_code}")
                    return cache_data.copy(), stock_code

            # 使用智能数据源获取数据
            df, standardized_code, source = self.smart_loader.load_stock_data(
                stock_code, period, start_date, end_date
            )
            
            if df.empty:
                st.error(f"❌ 无法获取股票 {stock_code} 的数据")
                return pd.DataFrame(), standardized_code

            # 更新缓存
            self._cache[cache_key] = (df.copy(), datetime.now())
            
            st.success(f"✅ 成功获取到 {standardized_code} 的历史数据 ({source})，共{len(df)}条记录")
            return df, standardized_code

        except Exception as e:
            st.error(f"❌ 加载数据失败: {str(e)}")
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
            info, source = self.smart_loader.get_market_info(stock_code)
            if info:
                info['data_source'] = source
                return info
            else:
                return {
                    'symbol': stock_code,
                    'error': '无法获取市场信息',
                    'data_source': 'none'
                }
        except Exception as e:
            return {
                'symbol': stock_code,
                'error': str(e),
                'data_source': 'error'
            }

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
