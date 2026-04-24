import pandas as pd
from typing import List, Tuple, Optional
from datetime import datetime
import logging

from src.config.settings import DataConfig

logger = logging.getLogger(__name__)


class StockDataLoader:
    def __init__(self, data_config: DataConfig):
        self.data_config = data_config
        self._cache: dict = {}
        self._cache_timeout = 300  # 缓存超时（秒）

        # 导入智能数据源（延迟，避免循环导入）
        from .smart_loader import get_smart_loader
        self.smart_loader = get_smart_loader(data_config)
        logger.info("StockDataLoader 初始化，使用智能数据源")

    def get_sz100_tickers(self) -> List[str]:
        """从本地 CSV 文件获取深证100指数成分股列表"""
        try:
            df = pd.read_csv(self.data_config.sz100_stocks_file)
            tickers = df['code'].tolist()
            return tickers
        except Exception as e:
            logger.error(f"读取股票列表失败: {str(e)}")
            return []

    def load_stock_data(
        self, stock_code: str, period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Tuple[pd.DataFrame, str]:
        """
        智能加载股票数据（支持多数据源自动切换）。

        Returns:
            (DataFrame, 标准化代码)
        """
        try:
            if not stock_code:
                logger.warning("股票代码不能为空")
                return pd.DataFrame(), ''

            # 缓存键包含所有参数，防止不同参数命中同一缓存
            cache_key = (stock_code, period, start_date, end_date)
            if cache_key in self._cache:
                cached_df, cached_time = self._cache[cache_key]
                age_seconds = (datetime.now() - cached_time).total_seconds()
                if age_seconds < self._cache_timeout:
                    logger.debug(f"使用缓存数据: {stock_code} (age={age_seconds:.0f}s)")
                    return cached_df.copy(), stock_code

            # 使用智能数据源获取数据
            df, standardized_code, source = self.smart_loader.load_stock_data(
                stock_code, period, start_date, end_date
            )

            if df.empty:
                logger.error(f"无法获取股票 {stock_code} 的数据")
                return pd.DataFrame(), standardized_code

            # 缓存（带参数化的 key）
            self._cache[cache_key] = (df.copy(), datetime.now())
            logger.info(
                f"成功获取 {standardized_code} 的历史数据 ({source})，共 {len(df)} 条记录"
            )
            return df, standardized_code

        except Exception as e:
            logger.error(f"加载数据失败: {str(e)}")
            return pd.DataFrame(), ''

    def get_market_info(self, stock_code: str) -> dict:
        """获取股票市场信息"""
        try:
            info, source = self.smart_loader.get_market_info(stock_code)
            if info:
                info['data_source'] = source
                return info
            return {
                'symbol': stock_code,
                'error': '无法获取市场信息',
                'data_source': 'none'
            }
        except Exception as e:
            logger.error(f"获取市场信息异常: {e}")
            return {
                'symbol': stock_code,
                'error': str(e),
                'data_source': 'error'
            }

    def batch_load_stock_data(
        self, stock_codes: List[str],
        progress_callback=None
    ) -> List[Tuple[pd.DataFrame, str]]:
        """
        批量加载多只股票数据。

        Args:
            progress_callback: (current, total, message) -> None，
                               替代直接依赖 st.progress/st.empty
        """
        results = []
        total = len(stock_codes)

        for i, code in enumerate(stock_codes):
            if progress_callback:
                progress_callback(i, total, f"正在处理 {i+1}/{total}: {code}")

            df, standardized_code = self.load_stock_data(code)
            results.append((df, standardized_code))

            if progress_callback:
                progress_callback(i + 1, total, f"完成 {i+1}/{total}: {code}")

        return results
