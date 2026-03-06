"""
AKShare数据加载器 - 专门为A股优化的免费数据源
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
import time
from typing import Tuple, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class AKShareDataLoader:
    """AKShare数据加载器 - 专门为A股市场设计"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.cache = {}  # 简单缓存机制
        self.cache_timeout = 300  # 5分钟缓存
        st.info("📊 使用AKShare数据源 - 专门为A股优化，完全免费")
    
    def load_stock_data(self, stock_code: str, period: str = "daily", 
                       start_date: Optional[str] = None, 
                       end_date: Optional[str] = None) -> Tuple[pd.DataFrame, str]:
        """
        使用AKShare加载A股股票数据
        
        Args:
            stock_code: 股票代码 (如: 002415, 000001.SZ)
            period: 周期 (daily, weekly, monthly)
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            
        Returns:
            (DataFrame, 标准化代码)
        """
        try:
            # 标准化代码
            standardized_code = self._standardize_code(stock_code)
            
            # 检查缓存
            cache_key = f"{standardized_code}_{period}_{start_date}_{end_date}"
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if time.time() - timestamp < self.cache_timeout:
                    st.info(f"📦 使用缓存数据: {standardized_code}")
                    return cached_data.copy(), standardized_code
            
            st.info(f"📡 正在通过AKShare获取 {standardized_code} 数据...")
            
            # 设置默认日期范围
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            
            # 获取历史数据
            df = ak.stock_zh_a_hist(
                symbol=standardized_code,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )
            
            if df.empty:
                st.warning(f"⚠️  未获取到 {standardized_code} 的历史数据")
                return pd.DataFrame(), standardized_code
            
            # 标准化数据格式
            df = self._standardize_akshare_data(df, standardized_code)
            
            # 缓存数据
            self.cache[cache_key] = (df.copy(), time.time())
            
            st.success(f"✅ 成功获取 {standardized_code} 数据: {len(df)} 条记录")
            return df, standardized_code
            
        except Exception as e:
            st.error(f"❌ AKShare数据获取失败: {e}")
            logger.error(f"AKShare数据获取失败: {e}", exc_info=True)
            return pd.DataFrame(), stock_code
    
    def get_real_time_quote(self, stock_code: str) -> Dict[str, Any]:
        """
        获取实时行情数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            实时行情字典
        """
        try:
            standardized_code = self._standardize_code(stock_code)
            
            # 获取所有A股实时行情
            spot_df = ak.stock_zh_a_spot()
            
            # 查找目标股票
            stock_data = spot_df[spot_df['代码'] == standardized_code]
            
            if not stock_data.empty:
                stock = stock_data.iloc[0]
                return {
                    'symbol': standardized_code,
                    'name': stock['名称'],
                    'latest_price': stock['最新价'],
                    'change_percent': stock['涨跌幅'],
                    'change_amount': stock['涨跌额'],
                    'volume': stock['成交量'],
                    'amount': stock['成交额'],
                    'open': stock['今开'],
                    'high': stock['最高'],
                    'low': stock['最低'],
                    'pre_close': stock['昨收'],
                    'amplitude': stock['振幅'],
                    'turnover_rate': stock['换手率'],
                    'pe_ratio': stock['市盈率-动态'],
                    'pb_ratio': stock['市净率'],
                    'timestamp': datetime.now().isoformat()
                }
            else:
                st.warning(f"⚠️  未找到 {standardized_code} 的实时行情")
                return {}
                
        except Exception as e:
            st.error(f"❌ 实时行情获取失败: {e}")
            return {}
    
    def get_fund_flow(self, stock_code: str, market: str = "SZ") -> pd.DataFrame:
        """
        获取资金流向数据
        
        Args:
            stock_code: 股票代码
            market: 市场 (SZ: 深交所, SH: 上交所)
            
        Returns:
            资金流向DataFrame
        """
        try:
            standardized_code = self._standardize_code(stock_code)
            df = ak.stock_individual_fund_flow(stock=standardized_code, market=market)
            return df
        except Exception as e:
            st.warning(f"资金流向数据获取失败: {e}")
            return pd.DataFrame()
    
    def get_minute_data(self, stock_code: str, period: str = "5") -> pd.DataFrame:
        """
        获取分时数据
        
        Args:
            stock_code: 股票代码
            period: 周期 (1, 5, 15, 30, 60)
            
        Returns:
            分时数据DataFrame
        """
        try:
            standardized_code = self._standardize_code(stock_code)
            df = ak.stock_zh_a_hist_min_em(symbol=standardized_code, period=period, adjust="")
            return df
        except Exception as e:
            st.warning(f"分时数据获取失败: {e}")
            return pd.DataFrame()
    
    def get_company_info(self, stock_code: str) -> Dict[str, Any]:
        """
        获取公司基本信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            公司信息字典
        """
        try:
            standardized_code = self._standardize_code(stock_code)
            df = ak.stock_individual_info_em(symbol=standardized_code)
            
            if not df.empty:
                info = {}
                for _, row in df.iterrows():
                    info[row['item']] = row['value']
                return info
            return {}
        except Exception as e:
            st.warning(f"公司信息获取失败: {e}")
            return {}
    
    def get_financial_data(self, stock_code: str) -> pd.DataFrame:
        """
        获取财务数据
        
        Args:
            stock_code: 股票代码
            
        Returns:
            财务数据DataFrame
        """
        try:
            standardized_code = self._standardize_code(stock_code)
            df = ak.stock_financial_report_sina(symbol=f"sz{standardized_code}" 
                                               if standardized_code.startswith('0') 
                                               else f"sh{standardized_code}")
            return df
        except Exception as e:
            st.warning(f"财务数据获取失败: {e}")
            return pd.DataFrame()
    
    def get_news(self, stock_code: str) -> pd.DataFrame:
        """
        获取股票新闻
        
        Args:
            stock_code: 股票代码
            
        Returns:
            新闻DataFrame
        """
        try:
            standardized_code = self._standardize_code(stock_code)
            df = ak.stock_news_em(symbol=standardized_code)
            return df
        except Exception as e:
            st.warning(f"新闻数据获取失败: {e}")
            return pd.DataFrame()
    
    def _standardize_code(self, code: str) -> str:
        """
        标准化股票代码
        
        Args:
            code: 原始股票代码
            
        Returns:
            标准化后的6位数字代码
        """
        code = str(code).strip().upper()
        
        # 去除后缀
        if '.' in code:
            code = code.split('.')[0]
        
        # 确保是6位数字
        if len(code) == 6 and code.isdigit():
            return code
        elif len(code) > 6:
            return code[-6:]  # 取最后6位
        else:
            # 补零到6位
            return code.zfill(6)
    
    def _standardize_akshare_data(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        标准化AKShare数据格式
        
        Args:
            df: 原始AKShare数据
            symbol: 股票代码
            
        Returns:
            标准化后的DataFrame
        """
        if df.empty:
            return df
        
        # 重命名列
        column_mapping = {
            '日期': 'Date',
            '开盘': 'Open',
            '收盘': 'Close',
            '最高': 'High',
            '最低': 'Low',
            '成交量': 'Volume',
            '成交额': 'Amount',
            '振幅': 'Amplitude',
            '涨跌幅': 'ChangePercent',
            '涨跌额': 'Change',
            '换手率': 'Turnover'
        }
        
        df = df.rename(columns=column_mapping)
        
        # 转换日期格式
        df['Date'] = pd.to_datetime(df['Date'])
        
        # 添加股票代码
        df['Symbol'] = symbol
        
        # 计算涨跌幅 (如果不存在)
        if 'ChangePercent' not in df.columns and 'Close' in df.columns:
            df['ChangePercent'] = df['Close'].pct_change() * 100
        
        # 计算涨跌额 (如果不存在)
        if 'Change' not in df.columns and 'Close' in df.columns:
            df['Change'] = df['Close'].diff()
        
        # 确保数据类型正确
        numeric_columns = ['Open', 'Close', 'High', 'Low', 'Volume', 'Amount', 
                          'Amplitude', 'ChangePercent', 'Change', 'Turnover']
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 按日期排序
        df = df.sort_values('Date').reset_index(drop=True)
        
        return df
    
    def get_market_info(self, stock_code: str) -> Dict[str, Any]:
        """
        获取市场信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            市场信息字典
        """
        standardized_code = self._standardize_code(stock_code)
        
        # 判断市场
        if standardized_code.startswith('0') or standardized_code.startswith('3'):
            market = 'SZ'
            market_name = '深圳证券交易所'
            suffix = '.SZ'
        elif standardized_code.startswith('6'):
            market = 'SH'
            market_name = '上海证券交易所'
            suffix = '.SS'
        else:
            market = 'Unknown'
            market_name = '未知市场'
            suffix = ''
        
        # 获取公司信息
        company_info = self.get_company_info(stock_code)
        name = company_info.get('股票简称', '') or company_info.get('公司名称', '')
        
        return {
            'symbol': standardized_code,
            'standardized_symbol': f"{standardized_code}{suffix}",
            'name': name,
            'market': market,
            'market_name': market_name,
            'currency': 'CNY',
            'timezone': 'Asia/Shanghai',
            'exchange': market_name,
            'country': 'China'
        }
    
    def test_connection(self) -> bool:
        """
        测试AKShare连接
        
        Returns:
            连接是否成功
        """
        try:
            # 尝试获取一只常见股票数据
            test_df = ak.stock_zh_a_spot()
            if not test_df.empty:
                st.success("✅ AKShare连接测试成功")
                return True
            else:
                st.warning("⚠️  AKShare连接测试返回空数据")
                return False
        except Exception as e:
            st.error(f"❌ AKShare连接测试失败: {e}")
            return False


# 快速测试函数
def test_akshare_loader():
    """测试AKShare数据加载器"""
    import streamlit as st
    
    st.title("AKShare数据加载器测试")
    
    loader = AKShareDataLoader()
    
    # 测试连接
    if loader.test_connection():
        st.success("✅ AKShare连接正常")
        
        # 测试002415
        stock_code = "002415"
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("测试实时行情"):
                quote = loader.get_real_time_quote(stock_code)
                if quote:
                    st.json(quote)
                else:
                    st.warning("未获取到实时行情")
        
        with col2:
            if st.button("测试历史数据"):
                df, code = loader.load_stock_data(stock_code, period="daily")
                if not df.empty:
                    st.write(f"获取到 {len(df)} 条数据")
                    st.dataframe(df.head())
                else:
                    st.warning("未获取到历史数据")
        
        # 测试其他功能
        if st.button("测试公司信息"):
            info = loader.get_company_info(stock_code)
            if info:
                st.json(info)
            else:
                st.warning("未获取到公司信息")
                
        if st.button("测试资金流向"):
            flow = loader.get_fund_flow(stock_code)
            if not flow.empty:
                st.dataframe(flow)
            else:
                st.warning("未获取到资金流向")


if __name__ == "__main__":
    test_akshare_loader()