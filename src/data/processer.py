import pandas as pd
import numpy as np
from typing import Tuple

class DataProcessor:
    """数据处理类"""
    
    @staticmethod
    def clean_data(data: pd.DataFrame) -> pd.DataFrame:
        """清理数据"""
        # 删除空值
        data = data.dropna()
        
        # 确保数据类型正确
        data['Date'] = pd.to_datetime(data['Date'])
        numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        data[numeric_columns] = data[numeric_columns].astype(float)
        
        return data

    @staticmethod
    def prepare_features(data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """准备特征数据"""
        # 计算基本特征
        data['Returns'] = data['Close'].pct_change()
        data['Volatility'] = data['Returns'].rolling(window=20).std()
        data['Price_Range'] = (data['High'] - data['Low']) / data['Close']
        
        # 移除包含NaN的行
        data = data.dropna()
        
        # 分离特征和目标
        features = data[['Returns', 'Volatility', 'Price_Range', 'Volume']]
        target = data['Close']
        
        return features, target

    @staticmethod
    def normalize_data(data: pd.DataFrame) -> pd.DataFrame:
        """归一化数据"""
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        data[numeric_columns] = (data[numeric_columns] - data[numeric_columns].mean()) / data[numeric_columns].std()
        return data