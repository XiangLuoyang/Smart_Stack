import streamlit as st
from datetime import datetime, date
import pandas as pd
import time
from io import BytesIO
import base64

from src.config.settings import AppConfig, DataConfig, ChartConfig, ModelConfig
from src.data.loader import StockDataLoader
# from src.data.processor import DataProcessor # DataProcessor is not used directly in smart-trade.py after changes
from src.models.technical import TechnicalIndicatorCalculator
from src.models.risk import RiskCalculator
# from src.models.prediction import ReturnPredictor # 移除机器学习预测器
from src.visualization.charts import ChartGenerator
from src.llm_analysis.core import create_financial_analysis_crew # <-- 新增导入
import plotly.graph_objects as go
# import plotly.io as pio # pio is not used
import os
import json
# import time # time is already imported

# 加载配置
app_config = AppConfig()
data_config = DataConfig()
chart_config = ChartConfig()
model_config = ModelConfig()

# 初始化
data_loader = StockDataLoader(data_config)
# data_processor = DataProcessor() # Not directly used here
indicator_calculator = TechnicalIndicatorCalculator()
risk_calculator = RiskCalculator(model_config)
# return_predictor = ReturnPredictor() # 移除机器学习预测器实例
chart_generator = ChartGenerator(chart_config)

# 设置页面配置
st.set_page_config(
    page_title=app_config.page_title,
    page_icon=app_config.page_icon,
    layout="wide"
)

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
    # ML_PREDS_CACHE_DIR = os.path.join(CACHE_BASE_DIR, "ml_predictions_cache") # 移除ML预测缓存目录
    LLM_REPORTS_CACHE_DIR = os.path.join(CACHE_BASE_DIR, "llm_reports_cache")
    
    # os.makedirs(ML_PREDS_CACHE_DIR, exist_ok=True) # 移除ML预测缓存目录创建
    os.makedirs(LLM_REPORTS_CACHE_DIR, exist_ok=True)

    # Cleanup old cache files on startup
    # cleanup_cache_by_mtime(ML_PREDS_CACHE_DIR, 7)  # 移除ML预测缓存清理
    cleanup_cache_by_mtime(LLM_REPORTS_CACHE_DIR, 7)

    try:
        # 应用标题
        st.title(app_config.page_title)
        
        # 侧边栏配置
        with st.sidebar:
            st.header("配置参数")
            analysis_mode = "单只股票分析" # 默认或固定为单股分析
            st.info("当前仅支持单只股票LLM分析。")  
            # 股票选择区域
            # if analysis_mode in ["单只股票分析", "两者都进行"]: # 简化条件，因为总是单股分析
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
                    
                    
                    # 更正后的代码：
                    # K线图等基本图表仍然可以显示，假设它不依赖ML预测结果
                    chart_generator.plot_stock_analysis(data) 

                    st.markdown("---") # 分隔线

                    # --- Section 2: LLM Deep Analysis with Caching ---
                    st.subheader(f"🤖 {selected_stock} LLM 深度分析报告")
                    today_str = datetime.now().strftime('%Y%m%d') # 确保 today_str 在这里定义，如果上面移除了
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
        elif not selected_stock and analysis_mode == "单只股票分析": # 确保此条件仍然合理
            st.info("👈 请在侧边栏选择一个股票代码开始分析")
            
    except Exception as e:
        st.error(f"程序运行出错: {str(e)}")

if __name__ == "__main__":
    main()
