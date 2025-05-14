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
from src.llm_analysis.core import create_financial_analysis_crew # <-- 新增导入
import plotly.graph_objects as go
import plotly.io as pio
import os 
import json 
import time # <-- 新增导入
# datetime is already imported from datetime import datetime, date

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
    layout="wide" # Changed from app_config.layout to a known valid literal
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

# Helper function for cache cleanup
def cleanup_cache_by_mtime(cache_dir_path: str, days_to_keep: int):
    if not os.path.isdir(cache_dir_path):
        return
    cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
    cleaned_count = 0
    for filename in os.listdir(cache_dir_path):
        file_path = os.path.join(cache_dir_path, filename)
        try:
            if os.path.isfile(file_path):
                if os.path.getmtime(file_path) < cutoff_time:
                    os.remove(file_path)
                    cleaned_count += 1
        except Exception as e:
            # Log discreetly or handle as per app's logging strategy
            # For a Streamlit app, st.warning might be too intrusive on every startup
            print(f"Warning: Error cleaning up cache file {filename}: {str(e)}") 
    if cleaned_count > 0:
        print(f"Cleaned up {cleaned_count} old files from {cache_dir_path}.")

def main():
    # Define and create cache directories under .cache/
    CACHE_BASE_DIR = ".cache"
    ML_PREDS_CACHE_DIR = os.path.join(CACHE_BASE_DIR, "ml_predictions_cache")
    LLM_REPORTS_CACHE_DIR = os.path.join(CACHE_BASE_DIR, "llm_reports_cache")
    
    os.makedirs(ML_PREDS_CACHE_DIR, exist_ok=True) # This creates .cache/ml_predictions_cache
    os.makedirs(LLM_REPORTS_CACHE_DIR, exist_ok=True) # This creates .cache/llm_reports_cache

    # Cleanup old cache files on startup
    cleanup_cache_by_mtime(ML_PREDS_CACHE_DIR, 7)  # Keep for 7 days
    cleanup_cache_by_mtime(LLM_REPORTS_CACHE_DIR, 7) # Keep for 7 days

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
            else: # analysis_mode is "沪深100股票分析"
                selected_stock = None
                # Provide default values for Pyright, even if not used in this path for ML prediction
                period = 30 
                start_date = datetime(2020, 1, 1)
                confidence_interval = 0.95

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
                                "股票代码": st.column_config.TextColumn("股票代码", width="medium"), # Changed width
                                "预期涨幅": st.column_config.TextColumn("预期涨幅", width="medium")  # Changed width
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
                                "股票代码": st.column_config.TextColumn("股票代码", width="medium"), # Changed width
                                "预期跌幅": st.column_config.TextColumn("预期跌幅", width="medium")  # Changed width
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
                    
                    today_str = datetime.now().strftime('%Y%m%d')

                    # --- Section 1: Machine Learning Analysis with Caching ---
                    st.subheader(f"📈 {selected_stock} 机器学习分析与预测")
                    ml_cache_filename = f"{selected_stock}_{today_str}_preds.json"
                    ml_cache_path = os.path.join(ML_PREDS_CACHE_DIR, ml_cache_filename)
                    prediction_results = None

                    if os.path.exists(ml_cache_path):
                        try:
                            with open(ml_cache_path, 'r', encoding='utf-8') as f:
                                prediction_results = json.load(f)
                            st.caption(f"机器学习预测结果加载自缓存 ({ml_cache_filename})")
                        except Exception as e_load_ml:
                            st.warning(f"加载机器学习缓存失败 ({ml_cache_filename}): {str(e_load_ml)}. 将重新计算。")
                            prediction_results = None # Ensure re-calculation

                    if prediction_results is None:
                        st.caption("正在计算机器学习预测...")
                        try:
                            # Convert date to datetime if it's a date object
                            start_datetime = datetime(start_date.year, start_date.month, start_date.day) if isinstance(start_date, date) and not isinstance(start_date, datetime) else start_date

                            prediction_results = return_predictor.calculate_expected_return(
                                selected_stock,
                                start_datetime, # Use converted datetime
                                period, # 来自侧边栏
                                confidence_interval # 来自侧边栏
                            )
                            if not prediction_results.get('error'):
                                try:
                                    with open(ml_cache_path, 'w', encoding='utf-8') as f:
                                        json.dump(prediction_results, f, indent=4, ensure_ascii=False)
                                    st.caption(f"机器学习预测结果已缓存至 {ml_cache_filename}")
                                except Exception as e_save_ml:
                                    st.warning(f"保存机器学习缓存失败 ({ml_cache_filename}): {str(e_save_ml)}")
                        except Exception as e_calc_ml:
                            st.error(f"执行机器学习预测计算时出错: {str(e_calc_ml)}")
                            import traceback
                            traceback.print_exc()
                            prediction_results = {'error': str(e_calc_ml)} # Ensure error is propagated

                    # Display ML results if available
                    if prediction_results and not prediction_results.get('error'):
                        chart_generator.plot_stock_analysis(data)
                        report_generator.generate_analysis_report(data, risk_metrics, prediction_results)
                    elif prediction_results and prediction_results.get('error'):
                        st.error(f"机器学习预测过程出错: {prediction_results['error']}")
                    else:
                        st.error("无法获取机器学习预测结果。")

                    st.markdown("---") # 分隔线

                    # --- Section 2: LLM Deep Analysis with Caching ---
                    st.subheader(f"🤖 {selected_stock} LLM 深度分析报告")
                    llm_cache_filename = f"{selected_stock}_{today_str}_llm_report.md"
                    llm_cache_path = os.path.join(LLM_REPORTS_CACHE_DIR, llm_cache_filename)
                    
                    final_llm_report_content = None # Variable to hold the report string for display

                    if os.path.exists(llm_cache_path):
                        try:
                            with open(llm_cache_path, 'r', encoding='utf-8') as f:
                                final_llm_report_content = f.read()
                            st.caption(f"LLM分析报告加载自缓存 ({llm_cache_filename})")
                        except Exception as e_load_llm:
                            st.warning(f"加载LLM报告缓存失败 ({llm_cache_filename}): {str(e_load_llm)}. 将重新生成。")
                            final_llm_report_content = None # Ensure re-generation
                    
                    if final_llm_report_content is None: # If not loaded from cache or cache load failed
                        st.caption("正在生成LLM分析报告...")
                        try:
                            llm_crew_output = None
                            with st.spinner(f'LLM 正在为 {selected_stock} 进行深度分析，请稍候...这可能需要几分钟。'):
                                llm_crew_output = create_financial_analysis_crew(selected_stock).kickoff()
                            
                            if llm_crew_output and hasattr(llm_crew_output, 'raw') and llm_crew_output.raw:
                                final_llm_report_content = llm_crew_output.raw
                            elif llm_crew_output: # Fallback if .raw is not the primary or suitable output
                                final_llm_report_content = str(llm_crew_output)
                            
                            if final_llm_report_content: # If we got some content
                                try:
                                    with open(llm_cache_path, 'w', encoding='utf-8') as f:
                                        f.write(final_llm_report_content)
                                    st.caption(f"LLM分析报告已缓存至 {llm_cache_filename}")
                                except Exception as e_save_llm:
                                    st.warning(f"保存LLM报告缓存失败 ({llm_cache_filename}): {str(e_save_llm)}")
                            else: # No valid content from LLM
                                st.warning("LLM执行完成，但未获取到有效报告文本。")
                                final_llm_report_content = "LLM未能生成有效报告文本。" # Set placeholder/error

                        except Exception as e_gen_llm:
                            st.error(f"生成LLM分析报告时发生错误: {str(e_gen_llm)}")
                            import traceback
                            traceback.print_exc()
                            final_llm_report_content = f"LLM报告生成失败: {str(e_gen_llm)}"

                    # Display LLM report
                    if final_llm_report_content:
                        # Check if it's one of our placeholder/error messages before rendering as markdown
                        if "LLM报告生成失败" in final_llm_report_content or "LLM未能生成有效报告文本" in final_llm_report_content:
                            st.error(final_llm_report_content)
                        else:
                            st.markdown(final_llm_report_content, unsafe_allow_html=True)
                    else: # Should ideally not be reached if logic above sets a placeholder
                        st.error(f"未能为 {selected_stock} 获取或生成LLM分析报告。")
                        
                except Exception as e_outer: # Outer try-except for data loading etc.
                    st.error(f"处理股票 {selected_stock} 的数据时发生错误: {str(e_outer)}")
                    import traceback
                    traceback.print_exc()
        elif not selected_stock and analysis_mode == "单只股票分析":
            st.info("👈 请在侧边栏选择一个股票代码开始分析")
            
    except Exception as e:
        st.error(f"程序运行出错: {str(e)}")

if __name__ == "__main__":
    main()
