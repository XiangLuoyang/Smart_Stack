import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from typing import Tuple, Dict

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