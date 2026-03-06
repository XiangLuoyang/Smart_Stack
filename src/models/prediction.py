import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Any
from scipy import stats
import streamlit as st
from sklearn.preprocessing import MinMaxScaler
import tensorflow as tf
import os
from dotenv import load_dotenv

# 使用 tf.keras 访问 Keras API
Sequential = tf.keras.models.Sequential
LSTM = tf.keras.layers.LSTM
Dense = tf.keras.layers.Dense
Dropout = tf.keras.layers.Dropout

# 导入统一数据加载器
from src.data.loader import StockDataLoader
from src.config.settings import DataConfig, ModelConfig

# Load environment variables
load_dotenv()

class ReturnPredictor:
    def __init__(self):
        try:
            # 初始化数据加载器（不再需要Tushare Token）
            data_config = DataConfig()
            self.data_loader = StockDataLoader(data_config)
            
            self.scaler = MinMaxScaler(feature_range=(0, 1))
            self.model = self._build_lstm_model()
            
            st.info("预测器已初始化，使用YFinance数据源")
        except Exception as e:
            st.error(f"初始化预测器失败: {str(e)}")
    
    def _build_lstm_model(self) -> Sequential:
        """构建LSTM模型"""
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
        
        # 使用收盘价
        close_prices = data['Close'].values.reshape(-1, 1)
        
        # 标准化数据
        scaled_data = self.scaler.fit_transform(close_prices)
        
        # 创建训练数据
        X, y = [], []
        for i in range(60, len(scaled_data)):
            X.append(scaled_data[i-60:i, 0])
            y.append(scaled_data[i, 0])
        
        X, y = np.array(X), np.array(y)
        X = np.reshape(X, (X.shape[0], X.shape[1], 1))
        
        return X, y
    
    def calculate_expected_return(
        self,
        ticker: str,
        start_date: datetime,
        window: int,
        confidence: float
    ) -> Dict[str, Any]:
        """计算预期日回报率和置信区间"""
        try:
            # 使用统一数据加载器获取数据
            hist_data, standardized_ticker = self.data_loader.load_stock_data(ticker)
            
            if hist_data.empty:
                return {
                    "error": f"无法获取 {ticker} 的历史数据",
                    "ticker": ticker,
                    "standardized_ticker": standardized_ticker
                }
            
            # 计算日回报率
            returns = hist_data['Close'].pct_change().dropna()
            
            if len(returns) < 30:
                return {
                    "error": f"数据不足，至少需要30个交易日数据，当前只有{len(returns)}个",
                    "ticker": ticker,
                    "standardized_ticker": standardized_ticker
                }
            
            # 计算统计指标
            mean_return = returns.mean()
            std_return = returns.std()
            
            # 计算置信区间
            z_score = stats.norm.ppf((1 + confidence) / 2)
            ci_lower = mean_return - z_score * std_return / np.sqrt(len(returns))
            ci_upper = mean_return + z_score * std_return / np.sqrt(len(returns))
            
            # 计算年化回报率
            annual_return = (1 + mean_return) ** 252 - 1
            
            return {
                "ticker": ticker,
                "standardized_ticker": standardized_ticker,
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
            return {
                "error": f"计算预期回报率失败: {str(e)}",
                "ticker": ticker
            }
    
    def train_lstm_model(self, data: pd.DataFrame, epochs: int = 50) -> Dict[str, Any]:
        """训练LSTM模型"""
        try:
            if data.empty or len(data) < 100:
                return {
                    "error": "数据不足，至少需要100个交易日数据",
                    "success": False
                }
            
            # 准备数据
            X, y = self._prepare_data(data)
            
            if len(X) == 0:
                return {
                    "error": "无法准备训练数据",
                    "success": False
                }
            
            # 训练模型
            history = self.model.fit(
                X, y,
                epochs=epochs,
                batch_size=32,
                validation_split=0.1,
                verbose=0
            )
            
            # 计算训练指标
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
            return {
                "error": f"训练LSTM模型失败: {str(e)}",
                "success": False
            }
    
    def predict_future_prices(self, data: pd.DataFrame, days: int = 5) -> Dict[str, Any]:
        """预测未来价格"""
        try:
            if data.empty or len(data) < 60:
                return {
                    "error": f"数据不足，至少需要60个交易日数据，当前只有{len(data)}个",
                    "success": False
                }
            
            # 准备最后60天的数据
            last_60_days = data['Close'].values[-60:].reshape(-1, 1)
            scaled_last_60_days = self.scaler.transform(last_60_days)
            
            # 重塑为LSTM输入格式
            X_test = np.array([scaled_last_60_days[:, 0]])
            X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))
            
            # 进行预测
            predictions = []
            current_batch = X_test
            
            for _ in range(days):
                current_pred = self.model.predict(current_batch, verbose=0)
                predictions.append(current_pred[0, 0])
                
                # 更新批次，添加预测值并移除最早的值
                current_batch = np.append(
                    current_batch[:, 1:, :],
                    current_pred.reshape(1, 1, 1),
                    axis=1
                )
            
            # 反标准化预测结果
            predictions = np.array(predictions).reshape(-1, 1)
            predictions = self.scaler.inverse_transform(predictions)
            
            # 生成预测日期
            last_date = data['Date'].max()
            prediction_dates = [
                last_date + pd.Timedelta(days=i+1) 
                for i in range(days)
            ]
            
            return {
                "success": True,
                "predictions": [
                    {
                        "date": date.strftime('%Y-%m-%d'),
                        "predicted_price": float(price[0])
                    }
                    for date, price in zip(prediction_dates, predictions)
                ],
                "last_actual_price": float(data['Close'].iloc[-1]),
                "last_actual_date": last_date.strftime('%Y-%m-%d'),
                "prediction_days": days
            }
            
        except Exception as e:
            return {
                "error": f"价格预测失败: {str(e)}",
                "success": False
            }
    
    def get_stock_recommendations(
        self,
        tickers: List[str],
        start_date: datetime,
        window: int,
        confidence: float
    ) -> Dict[str, List[Tuple[str, float]]]:
        """获取股票推荐列表"""
        buy_recommendations = []
        sell_recommendations = []
        
        total = len(tickers)
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, ticker in enumerate(tickers):
            status_text.text(f"分析 {i+1}/{total}: {ticker}")
            
            try:
                # 计算预期回报率
                result = self.calculate_expected_return(ticker, start_date, window, confidence)
                
                if "error" in result:
                    continue
                
                expected_return = result["expected_daily_return"]
                
                # 根据预期回报率分类
                if expected_return > 0.001:  # 日回报率大于0.1%
                    buy_recommendations.append((ticker, expected_return))
                elif expected_return < -0.001:  # 日回报率小于-0.1%
                    sell_recommendations.append((ticker, expected_return))
                
            except Exception as e:
                st.warning(f"分析 {ticker} 时出错: {str(e)}")
            
            progress_bar.progress((i + 1) / total)
        
        progress_bar.empty()
        status_text.empty()
        
        # 按预期回报率排序
        buy_recommendations.sort(key=lambda x: x[1], reverse=True)
        sell_recommendations.sort(key=lambda x: x[1])
        
        return {
            "buy": buy_recommendations[:10],  # 只返回前10个
            "sell": sell_recommendations[:10]
        }
