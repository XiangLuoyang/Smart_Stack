import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from scipy import stats
from sklearn.preprocessing import MinMaxScaler
import logging

# TensorFlow is optional — if not available, falls back to statistical methods
try:
    import tensorflow as tf
    LSTM_AVAILABLE = True
    Sequential = tf.keras.models.Sequential
    LSTM = tf.keras.layers.LSTM
    Dense = tf.keras.layers.Dense
    Dropout = tf.keras.layers.Dropout
except ImportError:
    LSTM_AVAILABLE = False
    tf = None
    Sequential = None
    LSTM = None
    Dense = None
    Dropout = None

from src.data.loader import StockDataLoader
from src.config.settings import DataConfig, ModelConfig

logger = logging.getLogger(__name__)


class ReturnPredictor:
    def __init__(self):
        try:
            data_config = DataConfig()
            self.data_loader = StockDataLoader(data_config)

            self.scaler = MinMaxScaler(feature_range=(0, 1))
            self.model = self._build_lstm_model()

            if LSTM_AVAILABLE:
                logger.info("预测器已初始化（LSTM可用），使用YFinance数据源")
            else:
                logger.info("预测器已初始化（TensorFlow未安装），使用统计方法")
        except Exception as e:
            logger.error(f"初始化预测器失败: {str(e)}")
            raise

    def _build_lstm_model(self) -> Optional[Sequential]:
        """构建LSTM模型"""
        if not LSTM_AVAILABLE:
            return None
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=(60, 1)),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])

        model.compile(optimizer='adam', loss='mean_squared_error')
        return model

    def _prepare_data(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """准备LSTM训练数据"""
        if data.empty:
            return np.array([]), np.array([])

        close_prices = data['Close'].values.reshape(-1, 1)
        scaled_data = self.scaler.fit_transform(close_prices)

        X, y = [], []
        for i in range(60, len(scaled_data)):
            X.append(scaled_data[i-60:i, 0])
            y.append(scaled_data[i, 0])

        X, y = np.array(X), np.array(y)
        X = np.reshape(X, (X.shape[0], X.shape[1], 1))

        return X, y

    def _train_lstm_on_data(self, data: pd.DataFrame, epochs: int = 10) -> bool:
        """
        在给定数据上训练LSTM模型（内部使用，不暴露给外部调用者）。
        训练较轻量（10 epochs），用于获取近期趋势感知的预测。
        """
        if not LSTM_AVAILABLE:
            return False
        try:
            X, y = self._prepare_data(data)
            if len(X) == 0:
                return False

            self.model.fit(X, y, epochs=epochs, batch_size=32, validation_split=0.1, verbose=0)
            return True
        except Exception as e:
            logger.warning(f"LSTM训练失败，回退到统计方法: {e}")
            return False

    def _lstm_predict_return(
        self,
        hist_data: pd.DataFrame,
        window: int,
        confidence: float
    ) -> Optional[Dict[str, Any]]:
        """
        使用LSTM模型预测预期收益和置信区间。
        训练最近60天数据，用滚动窗口思想做单步/几步预测，
        再统计预测收益率的均值和标准差来构建置信区间。
        返回 None 表示LSTM路径不可用。
        """
        if not LSTM_AVAILABLE:
            return None
        try:
            # 取最近数据训练（至少需要60天）
            train_data = hist_data.tail(min(252, len(hist_data))).copy()
            if len(train_data) < 60:
                return None

            # 轻量训练（5 epochs，保持响应速度）
            trained = self._train_lstm_on_data(train_data, epochs=5)
            if not trained:
                return None

            # 多次预测模拟蒙特卡洛（20次），取预测收益率分布
            last_60 = train_data['Close'].values[-60:].reshape(-1, 1)
            scaled = self.scaler.transform(last_60)

            predicted_returns = []
            for _ in range(20):
                batch = scaled.reshape(1, 60, 1)
                pred = self.model.predict(batch, verbose=0)[0, 0]
                # 反标准化
                pred_price = self.scaler.inverse_transform([[pred]])[0, 0]
                actual_last = float(train_data['Close'].iloc[-1])
                ret = (pred_price - actual_last) / actual_last
                predicted_returns.append(ret)

            predicted_returns = np.array(predicted_returns)
            mean_return = float(np.mean(predicted_returns))
            std_return = float(np.std(predicted_returns))

            # 置信区间
            z_score = stats.norm.ppf((1 + confidence) / 2)
            ci_lower = mean_return - z_score * std_return
            ci_upper = mean_return + z_score * std_return

            annual_return = (1 + mean_return) ** 252 - 1

            return {
                "method": "lstm",
                "expected_daily_return": mean_return,
                "daily_std": std_return,
                "confidence_interval": {
                    "lower": float(ci_lower),
                    "upper": float(ci_upper),
                    "confidence": confidence
                },
                "annualized_return": float(annual_return),
                "simulation_runs": 20,
                "data_points": len(train_data),
                "start_date": train_data['Date'].min().strftime('%Y-%m-%d'),
                "end_date": train_data['Date'].max().strftime('%Y-%m-%d')
            }
        except Exception as e:
            logger.warning(f"LSTM预测路径异常，回退到统计方法: {e}")
            return None

    def calculate_expected_return(
        self,
        ticker: str,
        start_date: datetime,
        window: int,
        confidence: float
    ) -> Dict[str, Any]:
        """
        计算预期日回报率和置信区间。
        优先使用LSTM预测，若失败则回退到统计方法。
        """
        try:
            hist_data, standardized_ticker = self.data_loader.load_stock_data(ticker)

            if hist_data.empty:
                return {
                    "error": f"无法获取 {ticker} 的历史数据",
                    "ticker": ticker,
                    "standardized_ticker": standardized_ticker
                }

            returns = hist_data['Close'].pct_change().dropna()

            if len(returns) < 30:
                return {
                    "error": f"数据不足，至少需要30个交易日数据，当前只有{len(returns)}个",
                    "ticker": ticker,
                    "standardized_ticker": standardized_ticker
                }

            # 优先尝试 LSTM 预测
            lstm_result = self._lstm_predict_return(hist_data, window, confidence)
            if lstm_result is not None:
                logger.info(f"{ticker}: 使用LSTM预测路径")
                return {
                    "ticker": ticker,
                    "standardized_ticker": standardized_ticker,
                    **lstm_result
                }

            # 回退到统计方法
            logger.info(f"{ticker}: LSTM不可用，使用统计方法")
            mean_return = returns.mean()
            std_return = returns.std()

            z_score = stats.norm.ppf((1 + confidence) / 2)
            ci_lower = mean_return - z_score * std_return / np.sqrt(len(returns))
            ci_upper = mean_return + z_score * std_return / np.sqrt(len(returns))

            annual_return = (1 + mean_return) ** 252 - 1

            return {
                "ticker": ticker,
                "standardized_ticker": standardized_ticker,
                "method": "statistical",
                "expected_daily_return": float(mean_return),
                "daily_std": float(std_return),
                "confidence_interval": {
                    "lower": float(ci_lower),
                    "upper": float(ci_upper),
                    "confidence": confidence
                },
                "annualized_return": float(annual_return),
                "data_points": len(returns),
                "start_date": hist_data['Date'].min().strftime('%Y-%m-%d'),
                "end_date": hist_data['Date'].max().strftime('%Y-%m-%d')
            }

        except Exception as e:
            logger.error(f"计算预期回报率失败: {str(e)}")
            return {
                "error": f"计算预期回报率失败: {str(e)}",
                "ticker": ticker
            }

    def train_lstm_model(self, data: pd.DataFrame, epochs: int = 50) -> Dict[str, Any]:
        """训练LSTM模型（显式调用接口，保留给需要深度训练的场景）"""
        try:
            if data.empty or len(data) < 100:
                return {
                    "error": "数据不足，至少需要100个交易日数据",
                    "success": False
                }

            X, y = self._prepare_data(data)
            if len(X) == 0:
                return {"error": "无法准备训练数据", "success": False}

            history = self.model.fit(
                X, y,
                epochs=epochs,
                batch_size=32,
                validation_split=0.1,
                verbose=0
            )

            train_loss = history.history['loss'][-1]
            val_loss = history.history.get('val_loss', [train_loss])[-1]

            return {
                "success": True,
                "epochs": epochs,
                "train_loss": float(train_loss),
                "val_loss": float(val_loss),
                "training_samples": len(X),
                "model_summary": "LSTM(50)-Dropout(0.2)-LSTM(50)-Dropout(0.2)-Dense(25)-Dense(1)"
            }

        except Exception as e:
            logger.error(f"训练LSTM模型失败: {str(e)}")
            return {"error": f"训练LSTM模型失败: {str(e)}", "success": False}

    def predict_future_prices(
        self, data: pd.DataFrame, days: int = 5
    ) -> Dict[str, Any]:
        """预测未来价格"""
        try:
            if data.empty or len(data) < 60:
                return {
                    "error": f"数据不足，至少需要60个交易日数据，当前只有{len(data)}个",
                    "success": False
                }

            last_date = data['Date'].max()
            last_price = float(data['Close'].iloc[-1])
            returns_series = data['Close'].pct_change().dropna()

            # 计算收益率统计量
            mean_daily_return = returns_series.mean()
            std_daily_return = returns_series.std()

            if LSTM_AVAILABLE and self.model is not None:
                # LSTM 路径：先 fit scaler 再用模型预测
                close_prices = data['Close'].values.reshape(-1, 1)
                self.scaler.fit(close_prices)

                last_60_days = data['Close'].values[-60:].reshape(-1, 1)
                scaled_last_60_days = self.scaler.transform(last_60_days)

                X_test = np.array([scaled_last_60_days[:, 0]])
                X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))

                predictions_scaled = []
                current_batch = X_test

                for _ in range(days):
                    current_pred = self.model.predict(current_batch, verbose=0)
                    predictions_scaled.append(current_pred[0, 0])
                    current_batch = np.append(
                        current_batch[:, 1:, :],
                        current_pred.reshape(1, 1, 1),
                        axis=1
                    )

                predictions_scaled = np.array(predictions_scaled).reshape(-1, 1)
                predictions = self.scaler.inverse_transform(predictions_scaled)
                method = "lstm_recursive"
                logger.warning(
                    f"predict_future_prices 使用递归多步预测，{days}天预测存在累积误差，"
                    "建议仅用于短期（≤5天）参考"
                )
            else:
                # 统计方法：用均值和标准差模拟随机游走
                predictions = []
                current_price = last_price
                for _ in range(days):
                    random_return = np.random.normal(mean_daily_return, std_daily_return)
                    current_price = current_price * (1 + random_return)
                    predictions.append(current_price)
                predictions = np.array(predictions).reshape(-1, 1)
                method = "statistical_monte_carlo"

            prediction_dates = [
                last_date + pd.Timedelta(days=i+1)
                for i in range(days)
            ]

            predicted_prices = [float(price[0]) for price in predictions]

            return {
                "success": True,
                "predicted_prices": predicted_prices,
                "last_actual_price": last_price,
                "last_actual_date": last_date.strftime('%Y-%m-%d'),
                "prediction_days": days,
                "method": method,
                "mean_daily_return": float(mean_daily_return),
                "std_daily_return": float(std_daily_return),
            }

        except Exception as e:
            logger.error(f"价格预测失败: {str(e)}")
            return {"error": f"价格预测失败: {str(e)}", "success": False}

    def get_stock_recommendations(
        self,
        tickers: List[str],
        start_date: datetime,
        window: int,
        confidence: float,
        progress_callback=None  # 回调接口，替代直接依赖 st.*
    ) -> Dict[str, List[Tuple[str, float]]]:
        """
        获取股票推荐列表。

        Args:
            progress_callback: 形如 callback(current, total, message) 的函数，
                                用于替代直接调用 st.progress/st.empty。
                                不传则静默执行。
        """
        buy_recommendations = []
        sell_recommendations = []

        total = len(tickers)

        for i, ticker in enumerate(tickers):
            if progress_callback:
                progress_callback(i, total, f"分析 {i+1}/{total}: {ticker}")

            try:
                result = self.calculate_expected_return(ticker, start_date, window, confidence)

                if "error" in result:
                    continue

                expected_return = result.get("expected_daily_return", 0)

                if expected_return > 0.001:
                    buy_recommendations.append((ticker, expected_return))
                elif expected_return < -0.001:
                    sell_recommendations.append((ticker, expected_return))

            except Exception as e:
                logger.warning(f"分析 {ticker} 时出错: {str(e)}")

            if progress_callback:
                progress_callback(i + 1, total, f"完成 {i+1}/{total}: {ticker}")

        buy_recommendations.sort(key=lambda x: x[1], reverse=True)
        sell_recommendations.sort(key=lambda x: x[1])

        return {
            "buy": buy_recommendations[:10],
            "sell": sell_recommendations[:10]
        }
