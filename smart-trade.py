import streamlit as st
from datetime import datetime, date
import pandas as pd
import time
from io import BytesIO
import base64

from src.config.settings import AppConfig, DataConfig, ChartConfig, ModelConfig
from src.data.loader import StockDataLoader
from src.data.processor import DataProcessor
from src.models.technical import TechnicalIndicatorCalculator
from src.models.risk import RiskCalculator
from src.models.prediction import ReturnPredictor
from src.visualization.charts import ChartGenerator
from src.visualization.reports import ReportGenerator
import plotly.graph_objects as go
import plotly.io as pio

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

def update_top_stocks():
    """更新Top10股票推荐列表"""
    tickers = data_loader.get_sz100_tickers()
    if not tickers:
        return
        
    # 创建进度条
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 获取所有股票的推荐
    recommendations = return_predictor.get_stock_recommendations(
        tickers,
        datetime(2020, 1, 1),
        30,
        0.95
    )
    
    # 更新session state中的推荐股票
    st.session_state.top_stocks = {
        'buy': [code for code, _ in recommendations['buy']],
        'sell': [code for code, _ in recommendations['sell']]
    }
    
    # 清除进度条和状态文本
    progress_bar.empty()
    status_text.empty()
    
    # 设置标志，表示已完成计算
    st.session_state.sz100_calculated = True
    st.success("沪深100股票分析完成！")

def main():
    try:
        # 初始化工作区缓存
        if 'top_stocks' not in st.session_state:
            st.session_state.top_stocks = {
                'buy': [],
                'sell': []
            }
        
        # 添加沪深100计算状态标志
        if 'sz100_calculated' not in st.session_state:
            st.session_state.sz100_calculated = False
        
        st.title(app_config.page_title)
        
        # 侧边栏配置
        with st.sidebar:
            st.header("配置参数")
            
            # 添加功能选择区域
            st.subheader("功能选择")
            analysis_mode = st.radio(
                "选择分析模式",
                ["单只股票分析", "沪深100股票分析", "两者都进行"]
            )
            
            # 如果选择了沪深100分析或两者都进行，显示计算按钮
            if analysis_mode in ["沪深100股票分析", "两者都进行"]:
                if st.button("开始计算沪深100股票") or (analysis_mode == "两者都进行" and not st.session_state.sz100_calculated):
                    update_top_stocks()
            
            # 股票选择区域
            if analysis_mode in ["单只股票分析", "两者都进行"]:
                st.subheader("股票选择")
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
                    value=datetime(2020, 1, 1),
                    min_value=datetime(2015, 1, 1),
                    max_value=date.today()
                )
                confidence_interval = st.slider("置信区间", 0.8, 0.99, 0.95)
            else:
                selected_stock = None

        # 显示沪深100分析结果
        if analysis_mode in ["沪深100股票分析", "两者都进行"] and st.session_state.sz100_calculated:
            with st.container():
                st.subheader("💼 沪深100智能分析")
                
                # 显示缓存中的Top10股票
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### 🚀 强烈推荐买入")
                    if st.session_state.top_stocks['buy']:
                        # 创建买入推荐表格数据
                        buy_data = {
                            '股票代码': [code for code in st.session_state.top_stocks['buy'][:10]],
                            '预期涨幅': ["--" for _ in st.session_state.top_stocks['buy'][:10]]
                        }
                        buy_df = pd.DataFrame(buy_data)
                        st.dataframe(
                            buy_df,
                            column_config={
                                "股票代码": st.column_config.TextColumn("股票代码", width=100),
                                "预期涨幅": st.column_config.TextColumn("预期涨幅", width=100)
                            },
                            hide_index=True
                        )
                    else:
                        st.info("暂无推荐股票，请点击计算按钮")
                
                with col2:
                    st.markdown("### 🚨 建议谨慎卖出")
                    if st.session_state.top_stocks['sell']:
                        # 创建卖出推荐表格数据
                        sell_data = {
                            '股票代码': [code for code in st.session_state.top_stocks['sell'][:10]],
                            '预期跌幅': ["--" for _ in st.session_state.top_stocks['sell'][:10]]
                        }
                        sell_df = pd.DataFrame(sell_data)
                        st.dataframe(
                            sell_df,
                            column_config={
                                "股票代码": st.column_config.TextColumn("股票代码", width=100),
                                "预期跌幅": st.column_config.TextColumn("预期跌幅", width=100)
                            },
                            hide_index=True
                        )
                    else:
                        st.info("暂无推荐股票，请点击计算按钮")
                
                # 截图下载按钮
                if st.button("📸 保存沪深100分析截图"):
                    try:
                        # 创建一个新的图表用于截图
                        fig = go.Figure()
                        
                        # 添加买入推荐数据
                        if st.session_state.top_stocks['buy']:
                            buy_text = "强烈推荐买入:\n" + "\n".join(
                                [f"{code}" for code in st.session_state.top_stocks['buy'][:10]]
                            )
                            fig.add_annotation(
                                text=buy_text,
                                x=0.25, y=0.5,
                                showarrow=False,
                                font=dict(size=14)
                            )
                        
                        # 添加卖出推荐数据
                        if st.session_state.top_stocks['sell']:
                            sell_text = "建议谨慎卖出:\n" + "\n".join(
                                [f"{code}" for code in st.session_state.top_stocks['sell'][:10]]
                            )
                            fig.add_annotation(
                                text=sell_text,
                                x=0.75, y=0.5,
                                showarrow=False,
                                font=dict(size=14)
                            )
                        
                        # 设置图表布局
                        fig.update_layout(
                            title="沪深100分析截图",
                            showlegend=False,
                            width=800,
                            height=600
                        )
                        
                        # 生成截图
                        img_bytes = fig.to_image(format="png")
                        b64 = base64.b64encode(img_bytes).decode()
                        href = f'<a href="data:image/png;base64,{b64}" download="sz100_snapshot.png">点击下载截图</a>'
                        st.markdown(href, unsafe_allow_html=True)
                        st.success("截图已生成，请点击链接下载")
                    except Exception as e:
                        st.error(f"生成截图时出错: {str(e)}")

        # 单只股票分析
        if selected_stock and analysis_mode in ["单只股票分析", "两者都进行"]:
            st.subheader(f"📊 {selected_stock} 个股分析")
            
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
        elif not selected_stock and analysis_mode == "单只股票分析":
            st.info("👈 请在侧边栏选择一个股票代码开始分析")
            
    except Exception as e:
        st.error(f"程序运行出错: {str(e)}")

if __name__ == "__main__":
    main()
