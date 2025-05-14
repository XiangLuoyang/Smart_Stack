import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Any # Added Any
from scipy import stats
import tushare as ts
import streamlit as st
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

class ReturnPredictor:
    def __init__(self):
        try:
            ts.set_token('5d35cfa04f7c37346fc16dbf860b6e8ea05cb5593ee956fed1d9bbc3')
            self.pro = ts.pro_api()
            self.scaler = MinMaxScaler(feature_range=(0, 1))
            self.model = self._build_lstm_model()
        except Exception as e:
            st.error(f"初始化Tushare API失败: {str(e)}")
    
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
        """准备LSTM模型训练数据"""
        scaled_data = self.scaler.fit_transform(data[['close']].values)
        x_train, y_train = [], []
        
        for i in range(60, len(scaled_data)):
            x_train.append(scaled_data[i-60:i, 0])
            y_train.append(scaled_data[i, 0])
            
        return np.array(x_train), np.array(y_train)

    def calculate_expected_return(
        self,
        ticker: str,
        start_date: datetime,
        days: int, # 'days' parameter is not currently used in the core return calculation logic after changes
        confidence: float
    ) -> Dict[str, Any]: # Changed return type hint to accommodate error dicts
        """计算预期日回报率和置信区间"""
        try:
            # 获取历史数据
            end_date = datetime.now()
            hist_data = self.pro.daily(
                ts_code=ticker,
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d')
            )
            
            if hist_data.empty:
                return {'error': '无法获取历史数据'}
            
            # 准备数据
            hist_data = hist_data.sort_values('trade_date')
            x_train, y_train = self._prepare_data(hist_data)
            
            # 训练LSTM模型
            self.model.fit(x_train, y_train, batch_size=32, epochs=10, verbose=0)
            
            # 准备预测数据
            last_60_days = self.scaler.transform(hist_data['close'].values[-60:].reshape(-1, 1))
            X_test = np.array([last_60_days])
            
            # LSTM预测
            lstm_pred = self.model.predict(X_test)
            lstm_pred = self.scaler.inverse_transform(lstm_pred)
            
            # 计算日回报率和日波动率
            returns = hist_data['close'].pct_change().dropna()
            if returns.empty:
                return {'error': '无法计算回报率，数据不足'}

            # 日均回报率 (百分比)
            daily_historical_mean_return_pct = returns.mean() * 100
            # 日波动率 (百分比)
            daily_volatility_pct = returns.std() * 100
            
            # LSTM预测的下一日回报率 (百分比)
            lstm_next_day_return_pct = ((lstm_pred[0][0] / hist_data['close'].iloc[-1]) - 1) * 100
            
            # 综合预期日回报率 (百分比)
            # 注意：这里的权重 (0.4, 0.6) 是经验值，可以调整
            expected_daily_return_pct = (daily_historical_mean_return_pct * 0.4 + lstm_next_day_return_pct * 0.6)
            
            # 计算基于日波动率的置信区间
            z_score = stats.norm.ppf((1 + confidence) / 2)
            margin_of_error_daily_pct = z_score * daily_volatility_pct
            
            return {
                'expected_daily_return_pct': expected_daily_return_pct,
                'daily_lower_bound_pct': expected_daily_return_pct - margin_of_error_daily_pct,
                'daily_upper_bound_pct': expected_daily_return_pct + margin_of_error_daily_pct,
                'lstm_predicted_next_price': lstm_pred[0][0], # 更准确的键名
                'daily_volatility_pct': daily_volatility_pct
                # 'forecast' 键被移除，因为它包含的是历史数据且未被图表生成器使用
            }
        except Exception as e:
            return {'error': f"计算预期收益时发生错误: {str(e)}"}

    def get_stock_recommendations(
        self,
        tickers: list,
        start_date: datetime,
        days: int,
        confidence: float
    ) -> Dict[str, list]:
        """获取股票推荐，包括最佳和最差表现"""
        try:
            results = []
            total_stocks = len(tickers)
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, ticker in enumerate(tickers, 1):
                progress = idx / total_stocks
                progress_bar.progress(progress)
                status_text.text(f'正在分析第 {idx}/{total_stocks} 支股票: {ticker}')
                
                prediction = self.calculate_expected_return(ticker, start_date, days, confidence)
                
                # Check for error first
                if prediction.get('error'):
                    # Optionally log the error for this specific ticker
                    # st.warning(f"Skipping {ticker} in recommendations due to error: {prediction['error']}")
                    continue

                # Use new keys and handle potential division by zero for volatility
                if 'expected_daily_return_pct' in prediction and 'daily_volatility_pct' in prediction:
                    daily_volatility = prediction['daily_volatility_pct']
                    if daily_volatility != 0:
                        score = prediction['expected_daily_return_pct'] * 0.7 + \
                               (1 / daily_volatility) * 30 * 0.3 # Using new keys
                        results.append((ticker, score))
                    else:
                        # Handle case where volatility is zero (e.g., constant price, rare)
                        # Assign a neutral or skip, or handle as per financial logic
                        # For now, we just append with a score that doesn't use inverse volatility part
                        score = prediction['expected_daily_return_pct'] * 0.7 
                        results.append((ticker, score))
                        
                    if len(results) >= 2:
                        sorted_results = sorted(results, key=lambda x: x[1], reverse=True)
                        st.session_state.top_stocks = {
                            'buy': [code for code, _ in sorted_results[:10]],
                            'sell': [code for code, _ in sorted_results[-10:] if len(sorted_results) >= 10]
                        }
            
            progress_bar.empty()
            status_text.empty()
            
            results.sort(key=lambda x: x[1], reverse=True)
            return {
                'buy': results[:10],
                'sell': results[-10:]
            }
        except Exception as e:
            st.error(f"获取股票推荐失败: {str(e)}")
            return {'buy': [], 'sell': []}
