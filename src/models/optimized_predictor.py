"""
优化版股票预测器 - 支持批量、并行、缓存
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional, Any, Callable
from datetime import datetime, timedelta
import concurrent.futures
import threading
import time
import json
import os
import logging
from dataclasses import dataclass
from enum import Enum
import hashlib
import pickle

from .prediction import ReturnPredictor

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """缓存策略"""
    NONE = "none"
    MEMORY = "memory"
    DISK = "disk"
    REDIS = "redis"


@dataclass
class CacheConfig:
    """缓存配置"""
    strategy: CacheStrategy = CacheStrategy.MEMORY
    ttl_seconds: int = 3600  # 1小时过期
    max_size: int = 1000  # 最大缓存条目数
    cache_dir: str = ".cache/recommendations"


class OptimizedReturnPredictor(ReturnPredictor):
    """
    优化版股票预测器
    支持批量获取、并行计算、智能缓存
    """

    def __init__(self, cache_config: Optional[CacheConfig] = None):
        super().__init__()
        self.cache_config = cache_config or CacheConfig()
        self._cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._init_cache()

    def _init_cache(self) -> None:
        """初始化缓存"""
        if self.cache_config.strategy == CacheStrategy.DISK:
            os.makedirs(self.cache_config.cache_dir, exist_ok=True)
            self._load_disk_cache()

    def _load_disk_cache(self) -> None:
        """从磁盘加载缓存"""
        try:
            cache_file = os.path.join(self.cache_config.cache_dir, "cache.pkl")
            if os.path.exists(cache_file):
                with open(cache_file, 'rb') as f:
                    self._cache = pickle.load(f)
                logger.info(f"从磁盘加载缓存: {len(self._cache)} 条记录")
        except Exception as e:
            logger.warning(f"缓存加载失败: {e}")

    def _save_disk_cache(self) -> None:
        """保存缓存到磁盘"""
        try:
            cache_file = os.path.join(self.cache_config.cache_dir, "cache.pkl")
            with open(cache_file, 'wb') as f:
                pickle.dump(self._cache, f)
        except Exception as e:
            logger.warning(f"缓存保存失败: {e}")

    def _get_cache_key(self, ticker: str, start_date: datetime,
                      window: int, confidence: float) -> str:
        """生成缓存键"""
        key_data = f"{ticker}_{start_date.strftime('%Y%m%d')}_{window}_{confidence}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """从缓存获取数据"""
        with self._cache_lock:
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                if time.time() - entry['timestamp'] < self.cache_config.ttl_seconds:
                    return entry['data']
                else:
                    del self._cache[cache_key]
            return None

    def _save_to_cache(self, cache_key: str, data: Dict) -> None:
        """保存数据到缓存"""
        with self._cache_lock:
            current_time = time.time()
            expired_keys = [
                k for k, v in self._cache.items()
                if current_time - v['timestamp'] > self.cache_config.ttl_seconds
            ]
            for key in expired_keys:
                del self._cache[key]

            if len(self._cache) >= self.cache_config.max_size:
                oldest_key = min(self._cache.keys(),
                               key=lambda k: self._cache[k]['timestamp'])
                del self._cache[oldest_key]

            self._cache[cache_key] = {'data': data, 'timestamp': current_time}

            if self.cache_config.strategy == CacheStrategy.DISK:
                if len(self._cache) % 10 == 0:
                    self._save_disk_cache()

    def calculate_expected_return_with_cache(
        self, ticker: str,
        start_date: datetime,
        window: int = 30,
        confidence: float = 0.95
    ) -> Dict:
        """带缓存的预期回报率计算"""
        cache_key = self._get_cache_key(ticker, start_date, window, confidence)

        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            logger.debug(f"使用缓存数据: {ticker}")
            return cached_result

        result = self.calculate_expected_return(ticker, start_date, window, confidence)
        self._save_to_cache(cache_key, result)
        return result

    def _process_single_stock(
        self, ticker: str, start_date: datetime,
        window: int, confidence: float
    ) -> Tuple[str, Optional[float]]:
        """处理单只股票（用于并行计算）"""
        try:
            result = self.calculate_expected_return_with_cache(
                ticker, start_date, window, confidence
            )

            if "error" in result:
                return ticker, None

            expected_return = result.get("expected_daily_return")
            return ticker, expected_return

        except Exception as e:
            logger.warning(f"分析 {ticker} 时出错: {str(e)}")
            return ticker, None

    def get_stock_recommendations_optimized(
        self,
        tickers: List[str],
        start_date: datetime,
        window: int = 30,
        confidence: float = 0.95,
        max_workers: int = 5,
        use_cache: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        优化版股票推荐获取，支持并行计算和缓存。

        Args:
            progress_callback: (current, total, message) -> None，
                               替代直接依赖 st.progress/st.empty。
        """
        if not tickers:
            return {"buy": [], "sell": []}

        buy_recommendations = []
        sell_recommendations = []

        total = len(tickers)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ticker = {
                executor.submit(
                    self._process_single_stock,
                    ticker, start_date, window, confidence
                ): ticker
                for ticker in tickers
            }

            completed = 0
            for future in concurrent.futures.as_completed(future_to_ticker):
                completed += 1
                ticker = future_to_ticker[future]

                try:
                    ticker, expected_return = future.result()

                    if expected_return is not None:
                        if expected_return > 0.001:
                            buy_recommendations.append((ticker, expected_return))
                        elif expected_return < -0.001:
                            sell_recommendations.append((ticker, expected_return))

                except Exception as e:
                    logger.warning(f"处理 {ticker} 结果时出错: {str(e)}")

                if progress_callback:
                    progress_callback(
                        completed, total,
                        f"处理进度: {completed}/{total} ({completed/total:.1%})"
                    )

        buy_recommendations.sort(key=lambda x: x[1], reverse=True)
        sell_recommendations.sort(key=lambda x: x[1])

        if self.cache_config.strategy == CacheStrategy.DISK:
            self._save_disk_cache()

        return {
            "buy": buy_recommendations[:10],
            "sell": sell_recommendations[:10]
        }

    def get_stock_recommendations_two_stage(
        self,
        tickers: List[str],
        start_date: datetime,
        window: int = 30,
        confidence: float = 0.95,
        quick_filter_threshold: float = 0.005,
        max_candidates: int = 30,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        两阶段筛选推荐：
        1. 快速技术指标筛选
        2. 详细AI预测计算
        """
        if not tickers:
            return {"buy": [], "sell": []}

        logger.info("第一阶段：快速技术指标筛选...")
        candidates = self._quick_technical_screening(
            tickers, start_date, quick_filter_threshold, max_candidates,
            progress_callback=progress_callback
        )

        logger.info(f"快速筛选完成，选出 {len(candidates)} 只候选股票")

        if not candidates:
            return {"buy": [], "sell": []}

        logger.info("第二阶段：详细AI预测计算...")
        return self.get_stock_recommendations_optimized(
            candidates, start_date, window, confidence,
            max_workers=3,
            progress_callback=progress_callback
        )

    def _quick_technical_screening(
        self,
        tickers: List[str],
        start_date: datetime,
        threshold: float = 0.005,
        max_candidates: int = 30,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[str]:
        """
        快速技术指标筛选。
        注意：此处传入的是 Close（大写），与 YFinance 返回格式一致。
        """
        from src.data.loader import StockDataLoader
        from src.config.settings import DataConfig
        from src.models.technical import TechnicalIndicatorCalculator

        data_loader = StockDataLoader(DataConfig())
        indicator_calculator = TechnicalIndicatorCalculator()

        candidates = []
        scores = []

        total = len(tickers)

        for i, ticker in enumerate(tickers):
            if progress_callback:
                progress_callback(i + 1, total, f"快速筛选: {i+1}/{total}")

            try:
                df, _ = data_loader.load_stock_data(ticker)
                if df is None or df.empty or len(df) < 20:
                    continue

                # 注意：使用 'Close'（大写），与项目数据格式一致
                close_col = 'Close' if 'Close' in df.columns else 'close'
                if close_col not in df.columns:
                    continue

                rsi = indicator_calculator.calculate_rsi(df)
                if rsi is None or rsi.isnull().all():
                    continue

                macd_result = indicator_calculator.calculate_macd(df)
                if macd_result is None:
                    continue
                macd_line, signal_line, _ = macd_result

                score = 0
                last_rsi = float(rsi.iloc[-1])
                last_macd = float(macd_line.iloc[-1])
                last_signal = float(signal_line.iloc[-1])

                # RSI 在 30-70 之间为佳
                if 30 < last_rsi < 70:
                    score += 1

                # MACD 金叉
                if not np.isnan(last_macd) and not np.isnan(last_signal):
                    if last_macd > last_signal:
                        score += 1

                # 近期上涨趋势
                recent_return = float(df[close_col].iloc[-1] / df[close_col].iloc[-5] - 1)
                if recent_return > 0:
                    score += 1

                # 波动率适中
                volatility = float(df[close_col].pct_change().std())
                if 0.01 < volatility < 0.05:
                    score += 1

                if score > 0:
                    scores.append((ticker, score))

            except Exception as e:
                logger.warning(f"快速筛选 {ticker} 时出错: {e}")

        scores.sort(key=lambda x: x[1], reverse=True)
        candidates = [ticker for ticker, score in scores[:max_candidates]]
        return candidates

    def get_recommendations_with_precomputation(
        self,
        tickers: List[str],
        precomputed_file: str = ".cache/precomputed_recommendations.json",
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        使用预计算结果，适合定期批量计算后快速查询。
        """
        try:
            if os.path.exists(precomputed_file):
                with open(precomputed_file, 'r') as f:
                    precomputed = json.load(f)

                file_mtime = os.path.getmtime(precomputed_file)
                if time.time() - file_mtime < 86400:  # 24小时
                    logger.info("使用预计算结果")
                    return precomputed
                else:
                    logger.warning("预计算结果已过期，重新计算...")
        except Exception as e:
            logger.warning(f"读取预计算结果失败: {e}")

        start_date = datetime.now() - timedelta(days=365)
        result = self.get_stock_recommendations_two_stage(
            tickers, start_date,
            progress_callback=progress_callback
        )

        try:
            os.makedirs(os.path.dirname(precomputed_file), exist_ok=True)
            with open(precomputed_file, 'w') as f:
                json.dump(result, f, indent=2)
            logger.info(f"预计算结果已保存: {precomputed_file}")
        except Exception as e:
            logger.warning(f"保存预计算结果失败: {e}")

        return result
