import streamlit as st
import logging
import sys
from datetime import datetime, date
import pandas as pd
import time
from io import BytesIO
import base64

# ============================================================================
# Logging 配置（必须在其他模块导入前设置）
# ============================================================================
def setup_logging():
    """配置根日志记录器"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # 避免重复添加 handler
    if not root.handlers:
        root.addHandler(handler)

    # 抑制 noisy 第三方库日志
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)

setup_logging()
logger = logging.getLogger(__name__)


# ============================================================================
# 业务模块导入（logging 配置完成后才可安全 import）
# ============================================================================
from src.config.settings import AppConfig, DataConfig, ChartConfig, ModelConfig
from src.data.loader import StockDataLoader
from src.data.processor import DataProcessor
from src.models.technical import TechnicalIndicatorCalculator
from src.models.risk import RiskCalculator
from src.models.prediction import ReturnPredictor
from src.visualization.charts import ChartGenerator
from src.visualization.reports import ReportGenerator
# LLM 分析模块：延迟导入，仅在需要时加载（避免 CrewAI 在非 LLM 分析路径上初始化开销）
import plotly.graph_objects as go
import plotly.io as pio
import os
import json


# ============================================================================
# 全局配置实例
# ============================================================================
app_config = AppConfig()
data_config = DataConfig()
chart_config = ChartConfig()
model_config = ModelConfig()

data_loader = StockDataLoader(data_config)
data_processor = DataProcessor()
indicator_calculator = TechnicalIndicatorCalculator()
risk_calculator = RiskCalculator(model_config)
return_predictor = ReturnPredictor()
chart_generator = ChartGenerator(chart_config)
report_generator = ReportGenerator()


# ============================================================================
# Streamlit 页面配置
# ============================================================================
st.set_page_config(
    page_title=app_config.page_title,
    page_icon=app_config.page_icon,
    layout="wide"
)


# ============================================================================
# 辅助函数
# ============================================================================

def make_stock_progress_callback(progress_bar, status_text):
    """创建绑定到 Streamlit UI 组件的进度回调闭包"""
    def callback(current: int, total: int, message: str):
        progress_bar.progress(current / total if total else 1.0)
        status_text.text(message)
    return callback


def cleanup_cache_by_mtime(cache_dir_path: str, days_to_keep: int) -> int:
    """清理过期缓存文件，返回清理的文件数量"""
    if not os.path.isdir(cache_dir_path):
        return 0
    cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
    cleaned = 0
    for filename in os.listdir(cache_dir_path):
        file_path = os.path.join(cache_dir_path, filename)
        try:
            if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff_time:
                os.remove(file_path)
                cleaned += 1
        except Exception as e:
            logger.warning(f"清理缓存文件 {filename} 失败: {e}")
    if cleaned > 0:
        logger.info(f"清理了 {cleaned} 个过期缓存文件: {cache_dir_path}")
    return cleaned


# ============================================================================
# 核心业务函数
# ============================================================================

def update_top_stocks():
    """
    更新沪深100 Top10 推荐列表（优化版）。
    通过 progress_callback 将 Streamlit UI 更新与业务逻辑解耦。
    """
    tickers = data_loader.get_sz100_tickers()
    if not tickers:
        st.error("无法获取股票列表")
        return

    progress_bar = st.progress(0)
    status_text = st.empty()
    strategy = st.session_state.get("calculation_strategy", "two_stage")

    try:
        # 延迟导入：仅在需要时加载，节省非批量分析场景的启动时间
        # noinspection PyProtectedMember
        from src.models.optimized_predictor import (
            OptimizedReturnPredictor,
            CacheConfig
        )
        from src.models.optimized_predictor import CacheStrategy

        cache_config = CacheConfig(
            strategy=CacheStrategy.MEMORY,
            ttl_seconds=3600,
            max_size=1000
        )
        optimized_predictor = OptimizedReturnPredictor(cache_config)
        start_date = datetime(2020, 1, 1)
        cb = make_stock_progress_callback(progress_bar, status_text)

        if strategy == "parallel":
            status_text.text("使用并行计算策略...")
            recommendations = optimized_predictor.get_stock_recommendations_optimized(
                tickers, start_date, 30, 0.95,
                max_workers=int(st.session_state.get("max_workers", 5)),
                progress_callback=cb
            )

        elif strategy == "two_stage":
            status_text.text("使用两阶段筛选策略...")
            recommendations = optimized_predictor.get_stock_recommendations_two_stage(
                tickers, start_date, 30, 0.95,
                quick_filter_threshold=0.005,
                max_candidates=30,
                progress_callback=cb
            )

        else:  # precomputed
            status_text.text("使用预计算结果...")
            recommendations = optimized_predictor.get_recommendations_with_precomputation(
                tickers,
                progress_callback=cb
            )

        st.session_state.top_stocks = {
            'buy': [code for code, _ in recommendations['buy']],
            'sell': [code for code, _ in recommendations['sell']]
        }
        st.session_state.sz100_calculated = True
        st.session_state.last_calculation_strategy = strategy
        st.session_state.last_calculation_time = datetime.now()

        progress_bar.progress(1.0)
        status_text.text(f"沪深100股票分析完成 (策略: {strategy})")
        buy_count = len(recommendations['buy'])
        sell_count = len(recommendations['sell'])
        st.info(f"推荐结果: {buy_count}只买入, {sell_count}只卖出")

    except Exception as e:
        st.error(f"优化计算失败: {str(e)}")
        logger.error(f"update_top_stocks 异常: {e}", exc_info=True)
        status_text.text("优化方法失败，使用原始方法...")
        update_top_stocks_original(progress_bar, status_text)

    finally:
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()


def update_top_stocks_original(progress_bar=None, status_text=None):
    """
    原始版本的沪深100更新函数（回退路径）。
    接收外部传入的 Streamlit 组件，避免在纯业务逻辑层直接依赖 st。
    """
    tickers = data_loader.get_sz100_tickers()
    if not tickers:
        return

    # 若未传入 UI 组件，则在函数内部创建（兼容直接调用场景）
    if progress_bar is None:
        progress_bar = st.progress(0)
    if status_text is None:
        status_text = st.empty()

    start_date = datetime(2020, 1, 1)
    cb = make_stock_progress_callback(progress_bar, status_text)

    recommendations = return_predictor.get_stock_recommendations(
        tickers,
        start_date,
        30,
        0.95,
        progress_callback=cb
    )

    st.session_state.top_stocks = {
        'buy': [code for code, _ in recommendations['buy']],
        'sell': [code for code, _ in recommendations['sell']]
    }

    progress_bar.empty()
    status_text.empty()
    st.session_state.sz100_calculated = True
    st.success("沪深100股票分析完成！")


# ============================================================================
# 主应用入口
# ============================================================================

def main():
    CACHE_BASE_DIR = ".cache"
    ML_PREDS_CACHE_DIR = os.path.join(CACHE_BASE_DIR, "ml_predictions_cache")
    LLM_REPORTS_CACHE_DIR = os.path.join(CACHE_BASE_DIR, "llm_reports_cache")

    os.makedirs(ML_PREDS_CACHE_DIR, exist_ok=True)
    os.makedirs(LLM_REPORTS_CACHE_DIR, exist_ok=True)

    cleanup_cache_by_mtime(ML_PREDS_CACHE_DIR, 7)
    cleanup_cache_by_mtime(LLM_REPORTS_CACHE_DIR, 7)

    try:
        if 'top_stocks' not in st.session_state:
            st.session_state.top_stocks = {'buy': [], 'sell': []}

        if 'sz100_calculated' not in st.session_state:
            st.session_state.sz100_calculated = False

        st.title(app_config.page_title)

        # ---------- 侧边栏 ----------
        with st.sidebar:
            st.header("配置参数")

            st.subheader("功能选择")
            analysis_mode = st.radio(
                "选择分析模式",
                ["单只股票分析", "沪深100股票分析", "两者都进行"]
            )

            if analysis_mode in ["沪深100股票分析", "两者都进行"]:
                if st.button("开始计算沪深100股票") or (
                    analysis_mode == "两者都进行" and not st.session_state.sz100_calculated
                ):
                    update_top_stocks()

            if analysis_mode in ["单只股票分析", "两者都进行"]:
                st.subheader("股票选择")
                tickers = data_loader.get_sz100_tickers()
                if not tickers:
                    st.error("无法获取股票列表")
                    return

                selected_stock = st.selectbox("选择股票代码", tickers, index=0 if tickers else None)

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
                period = 30
                start_date = datetime(2020, 1, 1)
                confidence_interval = 0.95

            with st.expander("⚡ 性能配置"):
                calculation_strategy = st.radio(
                    "计算策略:",
                    ["two_stage", "parallel", "precomputed"],
                    index=0,
                    help="两阶段筛选(推荐)/并行计算/预计算"
                )
                st.session_state.calculation_strategy = calculation_strategy

                cache_enabled = st.checkbox("启用缓存", value=True,
                                          help="启用缓存可大幅提升后续计算速度")
                st.session_state.cache_enabled = cache_enabled

                if cache_enabled:
                    max_workers = st.slider("并行数量", 1, 10, 5,
                                           help="同时处理的股票数量")
                    st.session_state.max_workers = max_workers
                    cache_ttl = st.slider("缓存有效期(小时)", 1, 24, 1,
                                         help="缓存数据的有效期")
                    st.session_state.cache_ttl = cache_ttl * 3600

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 清除缓存"):
                        import shutil
                        if os.path.exists(".cache"):
                            shutil.rmtree(".cache")
                            os.makedirs(".cache", exist_ok=True)
                        st.success("缓存已清除")
                with col2:
                    if st.button("📊 性能统计"):
                        _show_performance_stats()

        # ---------- 沪深100 结果展示 ----------
        if (analysis_mode in ["沪深100股票分析", "两者都进行"]
                and st.session_state.sz100_calculated):
            with st.container():
                st.subheader("💼 沪深100智能分析")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### 🚀 强烈推荐买入")
                    if st.session_state.top_stocks['buy']:
                        buy_data = {
                            '股票代码': st.session_state.top_stocks['buy'][:10],
                            '预期涨幅': ["--"] * len(st.session_state.top_stocks['buy'][:10])
                        }
                        st.dataframe(
                            pd.DataFrame(buy_data),
                            column_config={
                                "股票代码": st.column_config.TextColumn("股票代码", width="medium"),
                                "预期涨幅": st.column_config.TextColumn("预期涨幅", width="medium")
                            },
                            hide_index=True
                        )
                    else:
                        st.info("暂无推荐股票，请点击计算按钮")

                with col2:
                    st.markdown("### 🚨 建议谨慎卖出")
                    if st.session_state.top_stocks['sell']:
                        sell_data = {
                            '股票代码': st.session_state.top_stocks['sell'][:10],
                            '预期跌幅': ["--"] * len(st.session_state.top_stocks['sell'][:10])
                        }
                        st.dataframe(
                            pd.DataFrame(sell_data),
                            column_config={
                                "股票代码": st.column_config.TextColumn("股票代码", width="medium"),
                                "预期跌幅": st.column_config.TextColumn("预期跌幅", width="medium")
                            },
                            hide_index=True
                        )
                    else:
                        st.info("暂无推荐股票，请点击计算按钮")

                if st.button("📸 保存沪深100分析截图"):
                    try:
                        fig = go.Figure()
                        if st.session_state.top_stocks['buy']:
                            buy_text = "强烈推荐买入:\n" + "\n".join(
                                st.session_state.top_stocks['buy'][:10]
                            )
                            fig.add_annotation(text=buy_text, x=0.25, y=0.5,
                                              showarrow=False, font=dict(size=14))

                        if st.session_state.top_stocks['sell']:
                            sell_text = "建议谨慎卖出:\n" + "\n".join(
                                st.session_state.top_stocks['sell'][:10]
                            )
                            fig.add_annotation(text=sell_text, x=0.75, y=0.5,
                                              showarrow=False, font=dict(size=14))

                        fig.update_layout(title="沪深100分析截图",
                                          showlegend=False, width=800, height=600)

                        img_bytes = fig.to_image(format="png")
                        b64 = base64.b64encode(img_bytes).decode()
                        href = f'<a href="data:image/png;base64,{b64}" download="sz100_snapshot.png">点击下载截图</a>'
                        st.markdown(href, unsafe_allow_html=True)
                        st.success("截图已生成，请点击链接下载")
                    except Exception as e:
                        st.error(f"生成截图时出错: {str(e)}")

        # ---------- 单只股票分析 ----------
        if selected_stock and analysis_mode in ["单只股票分析", "两者都进行"]:
            st.subheader(f"📊 {selected_stock} 个股分析")

            with st.spinner('正在加载数据...'):
                data, stock_name = data_loader.load_stock_data(selected_stock)

                if data.empty:
                    st.error("无法加载股票数据，请检查股票代码是否正确")
                    return

                data['Date'] = pd.to_datetime(data['Date']).dt.tz_localize(None)

                try:
                    data = indicator_calculator.add_all_indicators(data)
                    risk_metrics = risk_calculator.calculate_risk_metrics(data)
                    today_str = datetime.now().strftime('%Y%m%d')

                    # -- Section 1: ML 预测 --
                    st.subheader(f"📈 {selected_stock} 机器学习分析与预测")
                    ml_cache_filename = f"{selected_stock}_{today_str}_preds.json"
                    ml_cache_path = os.path.join(ML_PREDS_CACHE_DIR, ml_cache_filename)
                    prediction_results = None

                    if os.path.exists(ml_cache_path):
                        try:
                            with open(ml_cache_path, 'r', encoding='utf-8') as f:
                                prediction_results = json.load(f)
                            st.caption(f"机器学习预测结果加载自缓存 ({ml_cache_filename})")
                        except Exception as e:
                            st.warning(f"加载机器学习缓存失败: {e}")
                            prediction_results = None

                    if prediction_results is None:
                        st.caption("正在计算机器学习预测...")
                        try:
                            start_dt = datetime(start_date.year, start_date.month, start_date.day) \
                                if isinstance(start_date, date) and not isinstance(start_date, datetime) \
                                else start_date

                            prediction_results = return_predictor.calculate_expected_return(
                                selected_stock, start_dt, period, confidence_interval
                            )

                            if not prediction_results.get('error'):
                                try:
                                    with open(ml_cache_path, 'w', encoding='utf-8') as f:
                                        json.dump(prediction_results, f, indent=4, ensure_ascii=False)
                                    st.caption(f"机器学习预测结果已缓存至 {ml_cache_filename}")
                                except Exception as e:
                                    st.warning(f"保存机器学习缓存失败: {e}")
                        except Exception as e:
                            st.error(f"执行机器学习预测计算时出错: {e}")
                            logger.error(f"ML预测异常: {e}", exc_info=True)
                            prediction_results = {'error': str(e)}

                    if prediction_results and not prediction_results.get('error'):
                        chart_generator.plot_stock_analysis(data)
                        report_generator.generate_analysis_report(
                            data, risk_metrics, prediction_results
                        )
                    elif prediction_results and prediction_results.get('error'):
                        st.error(f"机器学习预测出错: {prediction_results['error']}")
                    else:
                        st.error("无法获取机器学习预测结果。")

                    st.markdown("---")

                    # -- Section 2: LLM 报告 --
                    st.subheader(f"🤖 {selected_stock} LLM 深度分析报告")
                    llm_cache_filename = f"{selected_stock}_{today_str}_llm_report.md"
                    llm_cache_path = os.path.join(LLM_REPORTS_CACHE_DIR, llm_cache_filename)
                    final_llm_report_content = None

                    if os.path.exists(llm_cache_path):
                        try:
                            with open(llm_cache_path, 'r', encoding='utf-8') as f:
                                final_llm_report_content = f.read()
                            st.caption(f"LLM分析报告加载自缓存 ({llm_cache_filename})")
                        except Exception as e:
                            st.warning(f"加载LLM报告缓存失败: {e}")
                            final_llm_report_content = None

                    if final_llm_report_content is None:
                        st.caption("正在生成LLM分析报告...")
                        try:
                            # 延迟导入 LLM 分析模块，仅在实际需要时加载
                            from src.llm_analysis.core import create_financial_analysis_crew

                            with st.spinner(
                                f'LLM 正在为 {selected_stock} 进行深度分析，请稍候...'
                            ):
                                llm_crew_output = create_financial_analysis_crew(
                                    selected_stock
                                ).kickoff()

                            if llm_crew_output and hasattr(llm_crew_output, 'raw') \
                                    and llm_crew_output.raw:
                                final_llm_report_content = llm_crew_output.raw
                            elif llm_crew_output:
                                final_llm_report_content = str(llm_crew_output)

                            if final_llm_report_content:
                                try:
                                    with open(llm_cache_path, 'w', encoding='utf-8') as f:
                                        f.write(final_llm_report_content)
                                    st.caption(f"LLM分析报告已缓存至 {llm_cache_filename}")
                                except Exception as e:
                                    st.warning(f"保存LLM报告缓存失败: {e}")
                            else:
                                final_llm_report_content = "LLM未能生成有效报告文本。"

                        except Exception as e:
                            st.error(f"生成LLM分析报告时发生错误: {e}")
                            logger.error(f"LLM报告生成异常: {e}", exc_info=True)
                            final_llm_report_content = f"LLM报告生成失败: {str(e)}"

                    if final_llm_report_content:
                        if ("LLM报告生成失败" in final_llm_report_content
                                or "LLM未能生成有效报告文本" in final_llm_report_content):
                            st.error(final_llm_report_content)
                        else:
                            st.markdown(final_llm_report_content, unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"处理股票 {selected_stock} 的数据时发生错误: {str(e)}")
                    logger.error(f"数据处理异常: {e}", exc_info=True)

        elif not selected_stock and analysis_mode == "单只股票分析":
            st.info("👈 请在侧边栏选择一个股票代码开始分析")

    except Exception as e:
        st.error(f"程序运行出错: {str(e)}")
        logger.error(f"main() 全局异常: {e}", exc_info=True)


def _show_performance_stats():
    """显示性能统计（内部使用，仅在 Streamlit 上下文中调用）"""
    if "performance_stats" not in st.session_state:
        st.session_state.performance_stats = {
            "total_calculations": 0,
            "total_time": 0.0,
            "avg_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "last_calculation": None
        }

    stats = st.session_state.performance_stats

    with st.expander("📊 详细性能统计", expanded=True):
        col1, col2, col3 = st.columns(3)
        col1.metric("总计算次数", stats["total_calculations"])
        col2.metric("总计算时间", f"{stats['total_time']:.1f}s")
        col3.metric("平均耗时", f"{stats['avg_time']:.1f}s")

        total = stats["cache_hits"] + stats["cache_misses"]
        hit_rate = f"{stats['cache_hits'] / total * 100:.1f}%" if total > 0 else "N/A"
        st.metric("缓存命中率", hit_rate)

        if stats["last_calculation"]:
            st.metric("上次计算", stats["last_calculation"].strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    main()
