import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from typing import Tuple, Dict
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from catboost import CatBoostRegressor
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StockPredictor:
    """股票预测模型类"""
    
    def __init__(self):
        self.model = RandomForestRegressor(
            n_estimators=100,
            random_state=42
        )
        self.scaler = StandardScaler()
        
    def prepare_data(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """准备训练数据"""
        # 创建特征
        data['Returns'] = data['Close'].pct_change()
        data['MA5'] = data['Close'].rolling(window=5).mean()
        data['MA20'] = data['Close'].rolling(window=20).mean()
        data['Volatility'] = data['Returns'].rolling(window=20).std()
        
        # 删除NaN值
        data = data.dropna()
        
        # 准备特征和目标
        features = data[['Returns', 'MA5', 'MA20', 'Volatility', 'Volume']].values
        target = data['Close'].values
        
        # 标准化特征
        features = self.scaler.fit_transform(features)
        
        return features, target
        
    def train(self, data: pd.DataFrame) -> Dict[str, float]:
        """训练模型"""
        # 准备数据
        features, target = self.prepare_data(data)
        
        # 分割训练集和测试集
        X_train, X_test, y_train, y_test = train_test_split(
            features, target, test_size=0.2, random_state=42
        )
        
        # 训练模型
        self.model.fit(X_train, y_train)
        
        # 评估模型
        train_score = self.model.score(X_train, y_train)
        test_score = self.model.score(X_test, y_test)
        
        return {
            'train_score': train_score,
            'test_score': test_score
        }
    
    def predict(self, data: pd.DataFrame) -> np.ndarray:
        """预测未来价格"""
        features, _ = self.prepare_data(data)
        return self.model.predict(features)

from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
import numpy as np

class EnhancedPrediction:
    def __init__(self):
        self.models = {
            'xgboost': XGBRegressor(),
            'lightgbm': LGBMRegressor(),
            'catboost': CatBoostRegressor(verbose=False)
        }
        self.scaler = StandardScaler()
        self.param_grids = {
            'xgboost': {'n_estimators': [100, 200], 'max_depth': [3, 5]},
            'lightgbm': {'n_estimators': [100, 200], 'num_leaves': [31, 50]},
            'catboost': {'iterations': [100, 200], 'depth': [6, 8]}
        }
        
    def feature_engineering(self, df):
        try:
            df = df.copy()
            
            # Basic features
            df['MA_20_50_cross'] = (df['MA20'] > df['MA50']).astype(int)
            df['RSI_signal'] = (df['RSI'] > 70).astype(int)
            df['volatility'] = df['Close'].pct_change().rolling(20).std()
            
            # Advanced features
            df['price_momentum'] = df['Close'].pct_change(5)
            df['volume_trend'] = df['Volume'].pct_change(5)
            df['trend'] = df['Close'].diff(5).rolling(5).mean()
            
            # Interaction features
            df['price_vol_ratio'] = df['Close'] / df['Volume'].rolling(5).mean()
            df['macd_strength'] = df['MACD'] / df['Close']
            
            return df.fillna(method='ffill').fillna(0)
            
        except Exception as e:
            logging.error(f"Feature engineering error: {e}")
            raise

    def prepare_features(self, df):
        feature_cols = [
            'MA5', 'MA20', 'MA50', 'MA60', 'RSI', 'MACD',
            'MA_20_50_cross', 'RSI_signal', 'volatility',
            'price_momentum', 'volume_trend', 'trend',
            'price_vol_ratio', 'macd_strength'
        ]
        
        # Ensure all features exist
        for col in feature_cols:
            if col not in df.columns:
                print(f"Warning: Missing feature {col}")
                df[col] = 0
                
        X = df[feature_cols]
        return self.scaler.fit_transform(X)

    def ensemble_predict(self, df, predict_days=5):
        try:
            logging.info("Starting feature engineering...")
            df = self.feature_engineering(df)
            
            logging.info("Splitting time series data...")
            tscv = TimeSeriesSplit(n_splits=5)
            
            logging.info("Preparing features and target...")
            X = self.prepare_features(df[:-predict_days])
            y = df['Close'].shift(-predict_days).iloc[:-predict_days]
            
            mask = ~y.isna()
            X = X[mask]
            y = y[mask]
            
            predictions = []
            confidences = []
            
            for name, model in self.models.items():
                logging.info(f"Training model: {name}")
                model_preds = []
                
                grid_search = GridSearchCV(model, self.param_grids[name], cv=tscv)
                grid_search.fit(X, y)
                best_model = grid_search.best_estimator_
                
                for train_idx, val_idx in tscv.split(X):
                    X_train, X_val = X[train_idx], X[val_idx]
                    y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
                    
                    best_model.fit(X_train, y_train)
                    pred = best_model.predict(X_val)
                    model_preds.append(pred)
                
                X_test = self.prepare_features(df[-predict_days:])
                pred = best_model.predict(X_test)
                predictions.append(pred)
                
                conf = 1 - np.std(model_preds) / np.mean(y)
                confidences.append(conf)
            
            weights = np.array(confidences) / sum(confidences)
            final_pred = np.average(predictions, weights=weights, axis=0)
            
            logging.info("Prediction completed successfully.")
            return {
                'predictions': final_pred,
                'confidence': np.mean(confidences),
                'model_weights': dict(zip(self.models.keys(), weights))
            }
            
        except Exception as e:
            logging.error(f"Prediction error: {e}")
            raise

    def generate_signals(self, current_price, predicted_price):
        """
        根据当前价格和预测价格生成交易信号
        """
        if predicted_price > current_price * 1.05:
            return {'action': 'Strong Buy', 'trend_analysis': '上升趋势', 'technical_analysis': '技术指标看涨', 'risk_assessment': '低风险', 'recommendation': '买入'}
        elif predicted_price > current_price:
            return {'action': 'Buy', 'trend_analysis': '上升趋势', 'technical_analysis': '技术指标看涨', 'risk_assessment': '中等风险', 'recommendation': '买入'}
        elif predicted_price < current_price * 0.95:
            return {'action': 'Strong Sell', 'trend_analysis': '下降趋势', 'technical_analysis': '技术指标看跌', 'risk_assessment': '高风险', 'recommendation': '卖出'}
        elif predicted_price < current_price:
            return {'action': 'Sell', 'trend_analysis': '下降趋势', 'technical_analysis': '技术指标看跌', 'risk_assessment': '中等风险', 'recommendation': '卖出'}
        else:
            return {'action': 'Hold', 'trend_analysis': '横盘整理', 'technical_analysis': '技术指标中性', 'risk_assessment': '中等风险', 'recommendation': '观望'}