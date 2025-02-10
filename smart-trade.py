import streamlit as st
from datetime import datetime, date, timedelta
import pandas as pd

from src.config.settings import AppConfig, DataConfig, ChartConfig, ModelConfig
from src.data.loader import StockDataLoader
from src.data.processor import DataProcessor
from src.models.technical import TechnicalIndicatorCalculator
from src.models.risk import RiskCalculator
from src.models.prediction import ReturnPredictor
from src.visualization.charts import ChartGenerator
from src.visualization.reports import ReportGenerator

# 加载配置
app_config = AppConfig()
data_config = DataConfig()
chart_config = ChartConfig()
model_config = ModelConfig()

# 初始化数据加载器、数据处理器、指标计算器、风险计算器、预测器、图表生成器和报告生成器
data_loader = StockDataLoader(data_config)
data_processor = DataProcessor()
indicator_calculator = TechnicalIndicatorCalculator()
risk_calculator = RiskCalculator(model_config)
return_predictor = ReturnPredictor()
chart_generator = ChartGenerator(chart_config)
report_generator = ReportGenerator()

# 设置页面配置
st.set_page_config(
    page_title=app_config.page_title,
    page_icon=app_config.page_icon,
    layout=app_config.layout
)

def main():
    try:
        st.title(app_config.page_title)
        
        # 侧边栏配置
        with st.sidebar:
            st.header("配置参数")
            tickers = data_loader.get_sz100_tickers()
            if not tickers:
                st.error("无法获取股票列表")
                return
                
            selected_stock = st.selectbox(
                "选择股票代码",
                tickers,
                index=0 if tickers else None
            )
            
            st.subheader("预测参数")
            period = st.slider("预测天数", 1, 365, 30)
            start_date = st.date_input(
                "选择起始日期",
                value=date.today(), # 默认设置为今天
                min_value=datetime(2015, 1, 1),
                max_value=date.today()
            )
            confidence_interval = st.slider("置信区间", 0.8, 0.99, 0.95)

        if selected_stock:
            with st.spinner('正在加载数据...'):
                # 加载和处理数据
                data, stock_name = data_loader.load_stock_data(selected_stock)
                
                if data.empty:
                    st.error("无法加载股票数据，请检查股票代码是否正确")
                    return
                    
                # 确保日期格式正确，并移除时区信息
                data['Date'] = pd.to_datetime(data['Date']).dt.tz_localize(None)
                
                try:
                    # 添加技术指标
                    data = indicator_calculator.add_all_indicators(data)
                    
                    # 计算风险指标
                    risk_metrics = risk_calculator.calculate_risk_metrics(data)
                    
                    # 计算预期收益率
                    prediction_results = return_predictor.calculate_expected_return(
                        selected_stock,
                        start_date,
                        period,
                        confidence_interval
                    )
                    
                    if prediction_results.get('error'):
                        st.error(f"预测过程出错: {prediction_results['error']}")
                        return
                    
                    # 展示图表
                    chart_generator.plot_stock_analysis(data, prediction_results['forecast'])
                    
                    # 生成分析报告
                    report_generator.generate_analysis_report(data, risk_metrics, prediction_results)
                    
                except Exception as e:
                    st.error(f"处理数据时发生错误: {str(e)}")
        else:
            st.info("👈 请在侧边栏选择一个股票代码开始分析")

        st.subheader("🔥 TOP 10 股票推荐")
        if st.button("生成 TOP10 股票推荐"):
            with st.spinner("正在分析股票，生成推荐..."):
                # 将 start_date 设置为 1 年前，以获取足够的数据计算收益率
                recommendation_start_date = date.today() - timedelta(days=365)
                top_10_stocks = return_predictor.get_top_stock_recommendations(
                    tickers=data_loader.get_sz100_tickers(),
                    start_date=recommendation_start_date, # 使用调整后的 start_date
                    days=period,
                    confidence=confidence_interval
                )

                if top_10_stocks:
                    st.markdown("根据预期收益率，以下是推荐买入的 TOP 10 股票：")
                    
                    # 使用表格展示 TOP 10 股票推荐
                    top_10_df = pd.DataFrame(top_10_stocks, columns=['股票代码', '预期收益率(%)'])
                    top_10_df['预期收益率(%)'] = top_10_df['预期收益率(%)'].map('{:.2f}%'.format) # 格式化收益率
                    st.dataframe(top_10_df, hide_index=True)
                else:
                    st.info("无法获取股票推荐信息。")


    except Exception as e:
        st.error(f"程序运行出错: {str(e)}")

if __name__ == '__main__':
    main()
