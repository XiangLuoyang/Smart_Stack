from datetime import datetime, date, time

class AppConfig:
    """应用程序全局配置"""
    TITLE = "📈 Smart Stack - A股分析预测系统"
    PAGE_CONFIG = {
        "page_title": "Smart Stack",
        "page_icon": "📈",
        "layout": "wide"
    }

class DataConfig:
    """数据相关配置"""
    # 文件路径
    STOCK_LIST_PATH = "data/sz100_stocks.csv"
    
    # 数据加载配置
    DEFAULT_PERIOD = "2y"
    API_TIMEOUT = 10
    RETRY_TIMES = 3
    
    # A股交易时间
    TRADING_HOURS = {
        "morning": (time(9, 30), time(11, 30)),
        "afternoon": (time(13, 0), time(15, 0))
    }
    
    # 日期范围
    DATE_RANGE = {
        "min_date": datetime(2015, 1, 1),
        "max_date": date.today()
    }

class AnalysisConfig:
    """分析相关配置"""
    # 技术指标参数
    MA_PERIODS = [5, 20, 60]
    RSI_PERIOD = 14
    MACD_PARAMS = {
        "fast": 12,
        "slow": 26,
        "signal": 9
    }
    
    # 风险分析参数
    RISK_FREE_RATE = 0.03
    TRADING_DAYS = 252

class ChartConfig:
    """图表相关配置"""
    COLORS = {
        "up": "#00aa00",
        "down": "#ff0000",
        "MA5": "orange",
        "MA20": "blue",
        "MA60": "purple"
    }
    
    LAYOUT = {
        "height": 800,
        "template": "plotly_dark",
        "showlegend": True
    }

class ModelConfig:
    # 模型参数
    PREDICTION_WINDOW = 5  # 预测窗口
    HISTORY_WINDOW = 60   # 历史窗口
    FEATURE_ENGINEERING = True
    ENSEMBLE_LEARNING = True
    
    # 评估指标
    METRICS = ['mse', 'mae', 'mape']
    
    # 模型超参数
    MODEL_PARAMS = {
        'xgboost': {'n_estimators': 100, 'learning_rate': 0.1},
        'lightgbm': {'num_leaves': 31, 'learning_rate': 0.1},
        'catboost': {'iterations': 100, 'learning_rate': 0.1}
    }
