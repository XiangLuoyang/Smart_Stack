"""技术指标计算(从 src/models/technical.py 迁移,去全局单例)。

TA-Lib 为可选依赖:未安装时回退纯 pandas 实现,与原行为一致。
"""
from __future__ import annotations

import logging
from typing import Tuple

import pandas as pd

logger = logging.getLogger(__name__)

try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    talib = None
    TALIB_AVAILABLE = False


class TechnicalIndicatorCalculator:
    """与原 src/models/technical.TechnicalIndicatorCalculator 行为一致。"""

    def calculate_ma(self, data: pd.DataFrame, period: int) -> pd.Series:
        return data["Close"].rolling(window=period).mean()

    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        if "Close" not in data.columns or data["Close"].isnull().all():
            return pd.Series(index=data.index, dtype="float64")
        if not TALIB_AVAILABLE:
            delta = data["Close"].diff()
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)
            avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
            rs = avg_gain / avg_loss.replace(0, pd.NA)
            return (100.0 - (100.0 / (1.0 + rs))).fillna(100.0)
        return talib.RSI(data["Close"], timeperiod=period)

    def calculate_macd(
        self, data: pd.DataFrame,
        fastperiod: int = 12, slowperiod: int = 26, signalperiod: int = 9,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        if "Close" not in data.columns or data["Close"].isnull().all():
            empty = pd.Series(index=data.index, dtype="float64")
            return empty, empty, empty
        if not TALIB_AVAILABLE:
            fast = data["Close"].ewm(span=fastperiod, adjust=False).mean()
            slow = data["Close"].ewm(span=slowperiod, adjust=False).mean()
            macd = fast - slow
            signal = macd.ewm(span=signalperiod, adjust=False).mean()
            return macd, signal, macd - signal
        return talib.MACD(
            data["Close"],
            fastperiod=fastperiod,
            slowperiod=slowperiod,
            signalperiod=signalperiod,
        )

    def calculate_bollinger_bands(
        self, data: pd.DataFrame,
        period: int = 20, nbdevup: int = 2, nbdevdn: int = 2, matype: int = 0,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        if "Close" not in data.columns or data["Close"].isnull().all():
            empty = pd.Series(index=data.index, dtype="float64")
            return empty, empty, empty
        if not TALIB_AVAILABLE:
            middle = data["Close"].rolling(window=period).mean()
            std = data["Close"].rolling(window=period).std(ddof=0)
            return middle + nbdevup * std, middle, middle - nbdevdn * std
        return talib.BBANDS(
            data["Close"],
            timeperiod=period,
            nbdevup=nbdevup,
            nbdevdn=nbdevdn,
            matype=matype,
        )

    def add_all_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """一次性加 MA/RSI/MACD/布林带到 DataFrame。"""
        try:
            data["MA5"] = self.calculate_ma(data, 5)
            data["MA20"] = self.calculate_ma(data, 20)
            data["MA60"] = self.calculate_ma(data, 60)
        except Exception as e:
            logger.warning(f"计算 MA 失败: {e}")
        try:
            data["RSI"] = self.calculate_rsi(data)
        except Exception as e:
            logger.warning(f"计算 RSI 失败: {e}")
        try:
            macd, signal, hist = self.calculate_macd(data)
            data["MACD"] = macd
            data["Signal_Line"] = signal
            data["MACD_Histogram"] = hist
        except Exception as e:
            logger.warning(f"计算 MACD 失败: {e}")
        try:
            upper, middle, lower = self.calculate_bollinger_bands(data)
            data["BB_Upper"] = upper
            data["BB_Middle"] = middle
            data["BB_Lower"] = lower
        except Exception as e:
            logger.warning(f"计算布林带失败: {e}")
        return data
