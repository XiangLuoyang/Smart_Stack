import pandas as pd
import logging

logger = logging.getLogger(__name__)

# TA-Lib 为可选依赖：未安装时回退到纯 pandas 实现，保证 README 所称"无需系统级 TA-Lib"成立。
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    talib = None
    TALIB_AVAILABLE = False


class TechnicalIndicatorCalculator:
    def calculate_ma(self, data: pd.DataFrame, period: int) -> pd.Series:
        """计算移动平均线 (使用 pandas)"""
        return data['Close'].rolling(window=period).mean()

    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算RSI (使用 TA-Lib)"""
        if 'Close' not in data.columns or data['Close'].isnull().all():
            return pd.Series(index=data.index, dtype='float64')
        if not TALIB_AVAILABLE:
            # Wilder 平滑（ewm alpha=1/period），与 talib 默认口径一致
            delta = data['Close'].diff()
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)
            avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
            rs = avg_gain / avg_loss.replace(0, pd.NA)
            return (100.0 - (100.0 / (1.0 + rs))).fillna(100.0)
        return talib.RSI(data['Close'], timeperiod=period)

    def calculate_macd(
        self, data: pd.DataFrame,
        fastperiod: int = 12, slowperiod: int = 26, signalperiod: int = 9
    ) -> tuple:
        """计算MACD (使用 TA-Lib)"""
        if 'Close' not in data.columns or data['Close'].isnull().all():
            empty_series = pd.Series(index=data.index, dtype='float64')
            return empty_series, empty_series, empty_series
        if not TALIB_AVAILABLE:
            fast = data['Close'].ewm(span=fastperiod, adjust=False).mean()
            slow = data['Close'].ewm(span=slowperiod, adjust=False).mean()
            macd = fast - slow
            signal = macd.ewm(span=signalperiod, adjust=False).mean()
            return macd, signal, macd - signal

        macd, macdsignal, macdhist = talib.MACD(
            data['Close'],
            fastperiod=fastperiod,
            slowperiod=slowperiod,
            signalperiod=signalperiod
        )
        return macd, macdsignal, macdhist

    def calculate_bollinger_bands(
        self, data: pd.DataFrame,
        period: int = 20, nbdevup: int = 2, nbdevdn: int = 2, matype: int = 0
    ) -> tuple:
        """计算布林带 (使用 TA-Lib)"""
        if 'Close' not in data.columns or data['Close'].isnull().all():
            empty_series = pd.Series(index=data.index, dtype='float64')
            return empty_series, empty_series, empty_series
        if not TALIB_AVAILABLE:
            middle = data['Close'].rolling(window=period).mean()
            std = data['Close'].rolling(window=period).std(ddof=0)  # talib 用总体标准差
            return middle + nbdevup * std, middle, middle - nbdevdn * std

        upperband, middleband, lowerband = talib.BBANDS(
            data['Close'],
            timeperiod=period,
            nbdevup=nbdevup,
            nbdevdn=nbdevdn,
            matype=matype
        )
        return upperband, middleband, lowerband

    def add_all_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """添加所有技术指标，返回 (data, failed_indicators)"""
        failed_indicators = []
        try:
            data['MA5'] = self.calculate_ma(data, 5)
            data['MA20'] = self.calculate_ma(data, 20)
            data['MA60'] = self.calculate_ma(data, 60)
        except Exception as e:
            logger.warning(f"计算MA指标失败: {e}")
            failed_indicators.extend(['MA5', 'MA20', 'MA60'])

        try:
            data['RSI'] = self.calculate_rsi(data)
        except Exception as e:
            logger.warning(f"计算RSI失败: {e}")
            failed_indicators.append('RSI')

        try:
            macd, signal_line, macd_histogram = self.calculate_macd(data)
            data['MACD'] = macd
            data['Signal_Line'] = signal_line
            data['MACD_Histogram'] = macd_histogram
        except Exception as e:
            logger.warning(f"计算MACD失败: {e}")
            failed_indicators.extend(['MACD', 'Signal_Line', 'MACD_Histogram'])

        try:
            upper_bb, middle_bb, lower_bb = self.calculate_bollinger_bands(data)
            data['BB_Upper'] = upper_bb
            data['BB_Middle'] = middle_bb
            data['BB_Lower'] = lower_bb
        except Exception as e:
            logger.warning(f"计算布林带失败: {e}")
            failed_indicators.extend(['BB_Upper', 'BB_Middle', 'BB_Lower'])

        if failed_indicators:
            logger.warning(f"以下指标计算失败（已跳过）: {failed_indicators}")

        return data
