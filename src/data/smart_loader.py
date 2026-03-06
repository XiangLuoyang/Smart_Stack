"""
智能数据源选择器 - 支持多数据源自动切换
"""

import pandas as pd
from typing import Tuple, Dict, Any, Optional
import streamlit as st
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SmartDataSource:
    """
    智能数据源选择器
    自动选择最佳数据源，支持故障转移
    """
    
    def __init__(self, config=None):
        self.config = config or {}
        self.data_sources = {}
        self.source_priority = []
        self.source_status = {}
        self.initialized = False
        
    def initialize_sources(self):
        """初始化所有数据源"""
        if self.initialized:
            return
            
        try:
            # 尝试导入AKShare数据源
            try:
                from .loader_akshare import AKShareDataLoader
                akshare_loader = AKShareDataLoader(self.config)
                self.data_sources['akshare'] = akshare_loader
                self.source_priority.append('akshare')
                st.info("✅ AKShare数据源已加载 - 专门为A股优化")
            except ImportError as e:
                st.warning(f"⚠️  AKShare数据源加载失败: {e}")
            
            # 尝试导入YFinance数据源
            try:
                from .loader import StockDataLoader
                yfinance_loader = StockDataLoader(self.config)
                self.data_sources['yfinance'] = yfinance_loader
                self.source_priority.append('yfinance')
                st.info("✅ YFinance数据源已加载 - 全球市场支持")
            except ImportError as e:
                st.warning(f"⚠️  YFinance数据源加载失败: {e}")
            
            # 测试数据源连接
            self._test_sources()
            
            if not self.data_sources:
                st.error("❌ 没有可用的数据源，请检查依赖安装")
            else:
                st.success(f"✅ 已加载 {len(self.data_sources)} 个数据源")
                self.initialized = True
                
        except Exception as e:
            st.error(f"❌ 数据源初始化失败: {e}")
            logger.error(f"数据源初始化失败: {e}", exc_info=True)
    
    def _test_sources(self):
        """测试所有数据源连接"""
        for source_name, source in self.data_sources.items():
            try:
                # 每个数据源可能有不同的测试方法
                if hasattr(source, 'test_connection'):
                    if source.test_connection():
                        self.source_status[source_name] = 'healthy'
                        st.success(f"✅ {source_name} 连接正常")
                    else:
                        self.source_status[source_name] = 'unhealthy'
                        st.warning(f"⚠️  {source_name} 连接异常")
                else:
                    # 如果没有测试方法，默认认为健康
                    self.source_status[source_name] = 'healthy'
                    st.info(f"ℹ️  {source_name} 未提供连接测试")
            except Exception as e:
                self.source_status[source_name] = 'failed'
                st.error(f"❌ {source_name} 连接测试失败: {e}")
    
    def get_best_source(self, stock_code: str) -> str:
        """
        根据股票代码选择最佳数据源
        
        Args:
            stock_code: 股票代码
            
        Returns:
            最佳数据源名称
        """
        self.initialize_sources()
        
        if not self.data_sources:
            return None
        
        # 判断股票类型
        code = str(stock_code).strip().upper()
        
        # A股判断逻辑
        is_a_share = False
        if len(code) >= 6:
            clean_code = code.split('.')[0] if '.' in code else code
            if clean_code.isdigit():
                if clean_code.startswith(('0', '3', '6')):
                    is_a_share = True
        
        # 选择策略
        if is_a_share:
            # A股优先使用AKShare
            if 'akshare' in self.data_sources and self.source_status.get('akshare') == 'healthy':
                return 'akshare'
            elif 'yfinance' in self.data_sources and self.source_status.get('yfinance') == 'healthy':
                return 'yfinance'
        else:
            # 非A股使用YFinance
            if 'yfinance' in self.data_sources and self.source_status.get('yfinance') == 'healthy':
                return 'yfinance'
            elif 'akshare' in self.data_sources and self.source_status.get('akshare') == 'healthy':
                return 'akshare'  # 作为备用
        
        # 按优先级返回第一个健康的数据源
        for source_name in self.source_priority:
            if source_name in self.data_sources and self.source_status.get(source_name) == 'healthy':
                return source_name
        
        # 如果没有健康的数据源，返回第一个可用的
        for source_name in self.source_priority:
            if source_name in self.data_sources:
                return source_name
        
        return None
    
    def load_stock_data(self, stock_code: str, period: str = "daily",
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> Tuple[pd.DataFrame, str, str]:
        """
        智能加载股票数据
        
        Args:
            stock_code: 股票代码
            period: 周期
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            (DataFrame, 标准化代码, 使用的数据源)
        """
        self.initialize_sources()
        
        if not self.data_sources:
            st.error("❌ 没有可用的数据源")
            return pd.DataFrame(), stock_code, 'none'
        
        # 选择最佳数据源
        best_source = self.get_best_source(stock_code)
        
        if not best_source:
            st.error("❌ 无法找到合适的数据源")
            return pd.DataFrame(), stock_code, 'none'
        
        st.info(f"📊 使用 {best_source} 数据源分析 {stock_code}")
        
        # 尝试首选数据源
        source = self.data_sources[best_source]
        try:
            if hasattr(source, 'load_stock_data'):
                df, std_code = source.load_stock_data(stock_code, period, start_date, end_date)
                if not df.empty:
                    st.success(f"✅ {best_source} 数据获取成功: {len(df)} 条记录")
                    return df, std_code, best_source
                else:
                    st.warning(f"⚠️  {best_source} 返回空数据，尝试备用数据源...")
            else:
                st.warning(f"⚠️  {best_source} 不支持load_stock_data方法")
        except Exception as e:
            st.warning(f"⚠️  {best_source} 数据获取失败: {e}")
            logger.warning(f"{best_source} 数据获取失败: {e}")
        
        # 如果首选数据源失败，尝试其他数据源
        for source_name, alt_source in self.data_sources.items():
            if source_name == best_source:
                continue
                
            if self.source_status.get(source_name) == 'healthy':
                st.info(f"🔄 尝试备用数据源: {source_name}")
                try:
                    if hasattr(alt_source, 'load_stock_data'):
                        df, std_code = alt_source.load_stock_data(stock_code, period, start_date, end_date)
                        if not df.empty:
                            st.success(f"✅ {source_name} 备用数据源成功: {len(df)} 条记录")
                            return df, std_code, source_name
                except Exception as e:
                    st.warning(f"⚠️  {source_name} 备用数据源也失败: {e}")
        
        st.error("❌ 所有数据源都失败")
        return pd.DataFrame(), stock_code, 'failed'
    
    def get_real_time_quote(self, stock_code: str) -> Tuple[Dict[str, Any], str]:
        """
        获取实时行情
        
        Args:
            stock_code: 股票代码
            
        Returns:
            (行情数据字典, 使用的数据源)
        """
        self.initialize_sources()
        
        best_source = self.get_best_source(stock_code)
        if not best_source:
            return {}, 'none'
        
        source = self.data_sources[best_source]
        try:
            if hasattr(source, 'get_real_time_quote'):
                quote = source.get_real_time_quote(stock_code)
                if quote:
                    return quote, best_source
        except Exception as e:
            st.warning(f"实时行情获取失败: {e}")
        
        # 尝试其他数据源
        for source_name, alt_source in self.data_sources.items():
            if source_name == best_source:
                continue
                
            try:
                if hasattr(alt_source, 'get_real_time_quote'):
                    quote = alt_source.get_real_time_quote(stock_code)
                    if quote:
                        return quote, source_name
            except:
                continue
        
        return {}, 'failed'
    
    def get_market_info(self, stock_code: str) -> Tuple[Dict[str, Any], str]:
        """
        获取市场信息
        
        Args:
            stock_code: 股票代码
            
        Returns:
            (市场信息字典, 使用的数据源)
        """
        self.initialize_sources()
        
        best_source = self.get_best_source(stock_code)
        if not best_source:
            return {}, 'none'
        
        source = self.data_sources[best_source]
        try:
            if hasattr(source, 'get_market_info'):
                info = source.get_market_info(stock_code)
                if info:
                    return info, best_source
        except Exception as e:
            st.warning(f"市场信息获取失败: {e}")
        
        # 尝试其他数据源
        for source_name, alt_source in self.data_sources.items():
            if source_name == best_source:
                continue
                
            try:
                if hasattr(alt_source, 'get_market_info'):
                    info = alt_source.get_market_info(stock_code)
                    if info:
                        return info, source_name
            except:
                continue
        
        return {}, 'failed'
    
    def get_available_sources(self) -> Dict[str, str]:
        """
        获取可用的数据源状态
        
        Returns:
            数据源状态字典
        """
        self.initialize_sources()
        return self.source_status.copy()
    
    def get_source_stats(self) -> Dict[str, Any]:
        """
        获取数据源统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            'total_sources': len(self.data_sources),
            'healthy_sources': sum(1 for status in self.source_status.values() if status == 'healthy'),
            'unhealthy_sources': sum(1 for status in self.source_status.values() if status == 'unhealthy'),
            'failed_sources': sum(1 for status in self.source_status.values() if status == 'failed'),
            'source_priority': self.source_priority.copy(),
            'available_sources': list(self.data_sources.keys()),
            'last_update': datetime.now().isoformat()
        }
        return stats


# 全局实例
_smart_loader_instance = None

def get_smart_loader(config=None):
    """获取智能数据加载器单例"""
    global _smart_loader_instance
    if _smart_loader_instance is None:
        _smart_loader_instance = SmartDataSource(config)
    return _smart_loader_instance


# 测试函数
def test_smart_loader():
    """测试智能数据加载器"""
    import streamlit as st
    
    st.title("智能数据源选择器测试")
    
    loader = get_smart_loader()
    
    # 显示数据源状态
    st.subheader("数据源状态")
    stats = loader.get_source_stats()
    st.json(stats)
    
    # 测试不同股票
    test_cases = [
        ("002415", "A股 - 海康威视"),
        ("000001", "A股 - 平安银行"),
        ("AAPL", "美股 - 苹果"),
        ("0700.HK", "港股 - 腾讯"),
    ]
    
    for stock_code, description in test_cases:
        st.subheader(f"测试: {stock_code} ({description})")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button(f"分析 {stock_code}", key=f"btn_{stock_code}"):
                with st.spinner(f"正在分析 {stock_code}..."):
                    df, std_code, source = loader.load_stock_data(stock_code)
                    if not df.empty:
                        st.success(f"✅ 分析成功 - 数据源: {source}")
                        st.write(f"标准化代码: {std_code}")
                        st.write(f"数据条数: {len(df)}")
                        st.dataframe(df.head())
                    else:
                        st.error(f"❌ 分析失败")
        
        with col2:
            if st.button(f"实时行情 {stock_code}", key=f"quote_{stock_code}"):
                quote, source = loader.get_real_time_quote(stock_code)
                if quote:
                    st.success(f"✅ 实时行情 - 数据源: {source}")
                    st.json(quote)
                else:
                    st.warning("未获取到实时行情")
        
        with col3:
            if st.button(f"市场信息 {stock_code}", key=f"market_{stock_code}"):
                info, source = loader.get_market_info(stock_code)
                if info:
                    st.success(f"✅ 市场信息 - 数据源: {source}")
                    st.json(info)
                else:
                    st.warning("未获取到市场信息")


if __name__ == "__main__":
    test_smart_loader()