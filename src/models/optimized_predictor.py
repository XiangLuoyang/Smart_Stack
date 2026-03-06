"""
优化版股票预测器 - 支持批量、并行、缓存
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta
import streamlit as st
import concurrent.futures
import threading
import time
import json
import os
from dataclasses import dataclass
from enum import Enum
import hashlib
import pickle

# 导入原有预测器
from .prediction import ReturnPredictor


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
        self._cache = {}  # 内存缓存
        self._cache_lock = threading.Lock()
        self._init_cache()
    
    def _init_cache(self):
        """初始化缓存"""
        if self.cache_config.strategy == CacheStrategy.DISK:
            os.makedirs(self.cache_config.cache_dir, exist_ok=True)
            self._load_disk_cache()
    
    def _load_disk_cache(self):
        """从磁盘加载缓存"""
        try:
            cache_file = os.path.join(self.cache_config.cache_dir, "cache.pkl")
            if os.path.exists(cache_file):
                with open(cache_file, 'rb') as f:
                    self._cache = pickle.load(f)
                st.info(f"📦 从磁盘加载缓存: {len(self._cache)} 条记录")
        except Exception as e:
            st.warning(f"缓存加载失败: {e}")
    
    def _save_disk_cache(self):
        """保存缓存到磁盘"""
        try:
            cache_file = os.path.join(self.cache_config.cache_dir, "cache.pkl")
            with open(cache_file, 'wb') as f:
                pickle.dump(self._cache, f)
        except Exception as e:
            st.warning(f"缓存保存失败: {e}")
    
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
                # 检查是否过期
                if time.time() - entry['timestamp'] < self.cache_config.ttl_seconds:
                    return entry['data']
                else:
                    # 过期，删除
                    del self._cache[cache_key]
            return None
    
    def _save_to_cache(self, cache_key: str, data: Dict):
        """保存数据到缓存"""
        with self._cache_lock:
            # 清理过期条目
            current_time = time.time()
            expired_keys = [
                k for k, v in self._cache.items()
                if current_time - v['timestamp'] > self.cache_config.ttl_seconds
            ]
            for key in expired_keys:
                del self._cache[key]
            
            # 如果缓存满了，删除最旧的条目
            if len(self._cache) >= self.cache_config.max_size:
                oldest_key = min(self._cache.keys(), 
                               key=lambda k: self._cache[k]['timestamp'])
                del self._cache[oldest_key]
            
            # 保存新条目
            self._cache[cache_key] = {
                'data': data,
                'timestamp': current_time
            }
            
            # 如果是磁盘缓存，定期保存
            if self.cache_config.strategy == CacheStrategy.DISK:
                if len(self._cache) % 10 == 0:  # 每10条保存一次
                    self._save_disk_cache()
    
    def calculate_expected_return_with_cache(self, ticker: str, 
                                           start_date: datetime,
                                           window: int = 30,
                                           confidence: float = 0.95) -> Dict:
        """带缓存的预期回报率计算"""
        cache_key = self._get_cache_key(ticker, start_date, window, confidence)
        
        # 尝试从缓存获取
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            st.info(f"📦 使用缓存数据: {ticker}")
            return cached_result
        
        # 计算新结果
        result = self.calculate_expected_return(ticker, start_date, window, confidence)
        
        # 保存到缓存
        self._save_to_cache(cache_key, result)
        
        return result
    
    def _process_single_stock(self, ticker: str, start_date: datetime,
                            window: int, confidence: float) -> Tuple[str, Optional[float]]:
        """处理单只股票（用于并行计算）"""
        try:
            result = self.calculate_expected_return_with_cache(
                ticker, start_date, window, confidence
            )
            
            if "error" in result:
                return ticker, None
            
            expected_return = result["expected_daily_return"]
            return ticker, expected_return
            
        except Exception as e:
            st.warning(f"分析 {ticker} 时出错: {str(e)}")
            return ticker, None
    
    def get_stock_recommendations_optimized(
        self,
        tickers: List[str],
        start_date: datetime,
        window: int = 30,
        confidence: float = 0.95,
        max_workers: int = 5,  # 限制并发数，避免被封
        use_cache: bool = True
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        优化版股票推荐获取
        支持并行计算和缓存
        """
        if not tickers:
            return {"buy": [], "sell": []}
        
        buy_recommendations = []
        sell_recommendations = []
        
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        total = len(tickers)
        
        # 使用线程池并行处理
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_ticker = {
                executor.submit(
                    self._process_single_stock, 
                    ticker, start_date, window, confidence
                ): ticker 
                for ticker in tickers
            }
            
            # 处理完成的任务
            completed = 0
            for future in concurrent.futures.as_completed(future_to_ticker):
                completed += 1
                ticker = future_to_ticker[future]
                
                try:
                    ticker, expected_return = future.result()
                    
                    if expected_return is not None:
                        if expected_return > 0.001:  # 日回报率大于0.1%
                            buy_recommendations.append((ticker, expected_return))
                        elif expected_return < -0.001:  # 日回报率小于-0.1%
                            sell_recommendations.append((ticker, expected_return))
                    
                except Exception as e:
                    st.warning(f"处理 {ticker} 结果时出错: {str(e)}")
                
                # 更新进度
                progress = completed / total
                progress_bar.progress(progress)
                status_text.text(f"处理进度: {completed}/{total} ({progress:.1%})")
        
        # 清除进度条
        progress_bar.empty()
        status_text.empty()
        
        # 按预期回报率排序
        buy_recommendations.sort(key=lambda x: x[1], reverse=True)
        sell_recommendations.sort(key=lambda x: x[1])
        
        # 保存磁盘缓存
        if self.cache_config.strategy == CacheStrategy.DISK:
            self._save_disk_cache()
        
        return {
            "buy": buy_recommendations[:10],  # 只返回前10个
            "sell": sell_recommendations[:10]
        }
    
    def get_stock_recommendations_two_stage(
        self,
        tickers: List[str],
        start_date: datetime,
        window: int = 30,
        confidence: float = 0.95,
        quick_filter_threshold: float = 0.005,  # 快速筛选阈值
        max_candidates: int = 30  # 最大候选股票数
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        两阶段筛选推荐
        1. 快速技术指标筛选
        2. 详细AI预测计算
        """
        if not tickers:
            return {"buy": [], "sell": []}
        
        # 第一阶段：快速技术指标筛选
        st.info("🔍 第一阶段：快速技术指标筛选...")
        candidates = self._quick_technical_screening(
            tickers, start_date, quick_filter_threshold, max_candidates
        )
        
        st.info(f"✅ 快速筛选完成，选出 {len(candidates)} 只候选股票")
        
        if not candidates:
            return {"buy": [], "sell": []}
        
        # 第二阶段：详细AI预测计算
        st.info("🧠 第二阶段：详细AI预测计算...")
        return self.get_stock_recommendations_optimized(
            candidates, start_date, window, confidence, max_workers=3
        )
    
    def _quick_technical_screening(
        self,
        tickers: List[str],
        start_date: datetime,
        threshold: float = 0.005,
        max_candidates: int = 30
    ) -> List[str]:
        """
        快速技术指标筛选
        使用简单的技术指标快速筛选出有潜力的股票
        """
        from src.data.loader import StockDataLoader
        from src.data.processor import DataProcessor
        from src.models.technical import TechnicalIndicatorCalculator
        
        data_loader = StockDataLoader()
        data_processor = DataProcessor()
        indicator_calculator = TechnicalIndicatorCalculator()
        
        candidates = []
        scores = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        total = len(tickers)
        
        for i, ticker in enumerate(tickers):
            try:
                # 获取数据
                data = data_loader.load_stock_data(ticker)
                if data is None or data.empty:
                    continue
                
                # 计算简单技术指标
                if len(data) > 20:
                    # 计算RSI
                    rsi = indicator_calculator.calculate_rsi(data['close'])
                    if rsi is None:
                        continue
                    
                    # 计算MACD
                    macd_result = indicator_calculator.calculate_macd(data['close'])
                    if macd_result is None:
                        continue
                    
                    macd_line, signal_line, _ = macd_result
                    
                    # 计算简单得分
                    score = 0
                    
                    # RSI在30-70之间为佳
                    if 30 < rsi.iloc[-1] < 70:
                        score += 1
                    
                    # MACD金叉
                    if macd_line.iloc[-1] > signal_line.iloc[-1]:
                        score += 1
                    
                    # 近期上涨趋势
                    recent_return = (data['close'].iloc[-1] / data['close'].iloc[-5] - 1)
                    if recent_return > 0:
                        score += 1
                    
                    # 波动率适中
                    volatility = data['close'].pct_change().std()
                    if 0.01 < volatility < 0.05:
                        score += 1
                    
                    scores.append((ticker, score))
                    
            except Exception as e:
                # 快速筛选，忽略错误
                pass
            
            # 更新进度
            progress = (i + 1) / total
            progress_bar.progress(progress)
            status_text.text(f"快速筛选: {i+1}/{total}")
        
        # 清除进度条
        progress_bar.empty()
        status_text.empty()
        
        # 按得分排序，选择前N个
        scores.sort(key=lambda x: x[1], reverse=True)
        candidates = [ticker for ticker, score in scores[:max_candidates]]
        
        return candidates
    
    def get_recommendations_with_precomputation(
        self,
        tickers: List[str],
        precomputed_file: str = ".cache/precomputed_recommendations.json"
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        使用预计算结果
        适合定期批量计算后快速查询
        """
        try:
            if os.path.exists(precomputed_file):
                with open(precomputed_file, 'r') as f:
                    precomputed = json.load(f)
                
                # 检查是否过期（比如超过1天）
                file_mtime = os.path.getmtime(precomputed_file)
                if time.time() - file_mtime < 86400:  # 24小时
                    st.info("📊 使用预计算结果")
                    return precomputed
                else:
                    st.warning("预计算结果已过期，重新计算...")
            else:
                st.info("未找到预计算结果，开始计算...")
                
        except Exception as e:
            st.warning(f"读取预计算结果失败: {e}")
        
        # 如果没有预计算结果或已过期，进行计算
        start_date = datetime.now() - timedelta(days=365)
        result = self.get_stock_recommendations_two_stage(tickers, start_date)
        
        # 保存预计算结果
        try:
            os.makedirs(os.path.dirname(precomputed_file), exist_ok=True)
            with open(precomputed_file, 'w') as f:
                json.dump(result, f, indent=2)
            st.success(f"✅ 预计算结果已保存: {precomputed_file}")
        except Exception as e:
            st.warning(f"保存预计算结果失败: {e}")
        
        return result