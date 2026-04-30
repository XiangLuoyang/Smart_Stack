class AppConfig:
    page_title = "股票数据分析与预测系统"
    page_icon = "📈"
    layout = "wide"

class DataConfig:
    sz100_stocks_file = "data/sz100_stocks.csv"

class ChartConfig:
    template = "plotly_dark"
    height = 800

class ModelConfig:
    risk_free_rate = 0.03  # 无风险利率
