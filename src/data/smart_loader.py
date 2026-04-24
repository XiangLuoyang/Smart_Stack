"""
智能数据源选择器 - 支持多数据源自动切换
"""

import pandas as pd
from typing import Tuple, Dict, Any, Optional
import logging
import time
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
        self._init_timestamp: Optional[datetime] = None

    def reset(self) -> None:
        """重置实例状态，允许重新初始化（测试或多实例场景）"""
        logger.info("重置 SmartDataSource 实例")
        self.data_sources = {}
        self.source_priority = []
        self.source_status = {}
        self.initialized = False
        self._init_timestamp = None

    def initialize_sources(self) -> None:
        """初始化所有数据源"""
        if self.initialized:
            logger.debug("数据源已初始化，跳过")
            return

        try:
            # 尝试导入 AKShare 数据源
            try:
                from .loader_akshare import AKShareDataLoader
                akshare_loader = AKShareDataLoader(self.config)
                self.data_sources['akshare'] = akshare_loader
                self.source_priority.append('akshare')
                logger.info("AKShare 数据源已加载（A股优化）")
            except ImportError as e:
                logger.warning(f"AKShare 数据源加载失败: {e}")

            # 尝试导入 YFinance 数据源
            try:
                from .loader import StockDataLoader
                yfinance_loader = StockDataLoader(self.config)
                self.data_sources['yfinance'] = yfinance_loader
                self.source_priority.append('yfinance')
                logger.info("YFinance 数据源已加载（全球市场）")
            except ImportError as e:
                logger.warning(f"YFinance 数据源加载失败: {e}")

            self._test_sources()

            if not self.data_sources:
                logger.error("没有可用的数据源，请检查依赖安装")
            else:
                logger.info(f"已加载 {len(self.data_sources)} 个数据源")
                self.initialized = True
                self._init_timestamp = datetime.now()

        except Exception as e:
            logger.error(f"数据源初始化失败: {e}", exc_info=True)

    def _test_sources(self) -> None:
        """测试所有数据源连接（轻量探测，不阻塞）"""
        for source_name, source in self.data_sources.items():
            try:
                # 优先使用数据源自身的 test_connection（若支持）
                if hasattr(source, 'test_connection'):
                    try:
                        healthy = source.test_connection()
                        self.source_status[source_name] = 'healthy' if healthy else 'unhealthy'
                        logger.info(f"{source_name} 连接测试: {'healthy' if healthy else 'unhealthy'}")
                        continue
                    except Exception:
                        pass  # 继续走默认逻辑

                # 默认：对已有 data_sources 设为 healthy（已通过 ImportError 过滤）
                self.source_status[source_name] = 'healthy'
                logger.debug(f"{source_name} 未提供 test_connection，默认 healthy")

            except Exception as e:
                self.source_status[source_name] = 'failed'
                logger.error(f"{source_name} 连接测试失败: {e}")

    def get_best_source(self, stock_code: str) -> Optional[str]:
        """
        根据股票代码选择最佳数据源。

        A股（0/3/6开头6位代码）优先 AKShare（国内数据更完整），
        美股/港股等使用 YFinance。
        """
        self.initialize_sources()

        if not self.data_sources:
            return None

        code = str(stock_code).strip().upper()

        # A股判断逻辑
        is_a_share = False
        if len(code) >= 6:
            clean_code = code.split('.')[0] if '.' in code else code
            if clean_code.isdigit():
                if clean_code.startswith(('0', '3', '6')):
                    is_a_share = True

        if is_a_share:
            # A股：优先 AKShare，备用 YFinance
            if 'akshare' in self.data_sources and self.source_status.get('akshare') == 'healthy':
                return 'akshare'
            elif 'yfinance' in self.data_sources and self.source_status.get('yfinance') == 'healthy':
                return 'yfinance'
        else:
            # 非A股：优先 YFinance，备用 AKShare
            if 'yfinance' in self.data_sources and self.source_status.get('yfinance') == 'healthy':
                return 'yfinance'
            elif 'akshare' in self.data_sources and self.source_status.get('akshare') == 'healthy':
                return 'akshare'

        # 按优先级返回第一个健康数据源
        for source_name in self.source_priority:
            if source_name in self.data_sources and self.source_status.get(source_name) == 'healthy':
                return source_name

        # 返回任意可用数据源
        for source_name in self.source_priority:
            if source_name in self.data_sources:
                return source_name

        return None

    def load_stock_data(
        self, stock_code: str, period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Tuple[pd.DataFrame, str, str]:
        """
        智能加载股票数据。

        Returns:
            (DataFrame, 标准化代码, 使用的数据源)
        """
        self.initialize_sources()

        if not self.data_sources:
            logger.error("没有可用的数据源")
            return pd.DataFrame(), stock_code, 'none'

        best_source = self.get_best_source(stock_code)

        if not best_source:
            logger.error("无法找到合适的数据源")
            return pd.DataFrame(), stock_code, 'none'

        logger.info(f"使用 {best_source} 数据源加载 {stock_code}")

        # 尝试首选数据源
        source = self.data_sources[best_source]
        try:
            if hasattr(source, 'load_stock_data'):
                df, std_code = source.load_stock_data(stock_code, period, start_date, end_date)
                if not df.empty:
                    logger.info(f"{best_source} 数据获取成功: {len(df)} 条记录")
                    return df, std_code, best_source
                else:
                    logger.warning(f"{best_source} 返回空数据，尝试备用数据源...")
            else:
                logger.warning(f"{best_source} 不支持 load_stock_data 方法")
        except Exception as e:
            logger.warning(f"{best_source} 数据获取失败: {e}")

        # 备用数据源
        for source_name, alt_source in self.data_sources.items():
            if source_name == best_source:
                continue

            if self.source_status.get(source_name) == 'healthy':
                logger.info(f"尝试备用数据源: {source_name}")
                try:
                    if hasattr(alt_source, 'load_stock_data'):
                        df, std_code = alt_source.load_stock_data(stock_code, period, start_date, end_date)
                        if not df.empty:
                            logger.info(f"{source_name} 备用数据源成功: {len(df)} 条记录")
                            return df, std_code, source_name
                except Exception as e:
                    logger.warning(f"{source_name} 备用数据源也失败: {e}")

        logger.error("所有数据源均失败")
        return pd.DataFrame(), stock_code, 'failed'

    def get_real_time_quote(self, stock_code: str) -> Tuple[Dict[str, Any], str]:
        """获取实时行情"""
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
            logger.warning(f"实时行情获取失败: {e}")

        for source_name, alt_source in self.data_sources.items():
            if source_name == best_source:
                continue
            try:
                if hasattr(alt_source, 'get_real_time_quote'):
                    quote = alt_source.get_real_time_quote(stock_code)
                    if quote:
                        return quote, source_name
            except Exception:
                continue

        return {}, 'failed'

    def get_market_info(self, stock_code: str) -> Tuple[Dict[str, Any], str]:
        """获取市场信息"""
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
            logger.warning(f"市场信息获取失败: {e}")

        for source_name, alt_source in self.data_sources.items():
            if source_name == best_source:
                continue
            try:
                if hasattr(alt_source, 'get_market_info'):
                    info = alt_source.get_market_info(stock_code)
                    if info:
                        return info, source_name
            except Exception:
                continue

        return {}, 'failed'

    def get_available_sources(self) -> Dict[str, str]:
        """获取可用的数据源状态"""
        self.initialize_sources()
        return self.source_status.copy()

    def get_source_stats(self) -> Dict[str, Any]:
        """获取数据源统计信息"""
        self.initialize_sources()
        return {
            'total_sources': len(self.data_sources),
            'healthy_sources': sum(1 for s in self.source_status.values() if s == 'healthy'),
            'unhealthy_sources': sum(1 for s in self.source_status.values() if s == 'unhealthy'),
            'failed_sources': sum(1 for s in self.source_status.values() if s == 'failed'),
            'source_priority': self.source_priority.copy(),
            'available_sources': list(self.data_sources.keys()),
            'init_timestamp': self._init_timestamp.isoformat() if self._init_timestamp else None
        }


# 全局单例（支持重置）
_smart_loader_instance: Optional[SmartDataSource] = None


def get_smart_loader(config=None) -> SmartDataSource:
    """获取智能数据加载器单例"""
    global _smart_loader_instance
    if _smart_loader_instance is None:
        _smart_loader_instance = SmartDataSource(config)
    return _smart_loader_instance


def reset_smart_loader() -> None:
    """重置全局单例（用于测试或多实例场景）"""
    global _smart_loader_instance
    if _smart_loader_instance is not None:
        _smart_loader_instance.reset()
    _smart_loader_instance = None
