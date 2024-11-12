import os
import sys
import streamlit as st

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.config.settings import AppConfig
from src.data.loader import StockDataLoader
from src.models.technical import TechnicalIndicators
from src.models.risk import RiskMetrics
from src.visualization.charts import StockCharts
from src.utils.helpers import format_number

def main():
    try:
        # 设置页面配置
        st.set_page_config(**AppConfig.PAGE_CONFIG)
        st.title(AppConfig.TITLE)

        # 侧边栏配置
        with st.sidebar:
            st.header("配置参数")
            
            # 初始化数据加载器
            data_loader = StockDataLoader()
            stock_codes = data_loader.get_sz100_tickers()
            
            if not stock_codes:
                st.error("无法获取股票列表")
                return
            
            # 股票选择
            selected_stock = st.selectbox(
                "选择股票代码",
                stock_codes
            )
            
            # 其他参数配置
            analysis_period = st.slider(
                "分析周期（天）",
                min_value=30,
                max_value=365,
                value=180
            )

        if selected_stock:
            with st.spinner('正在加载数据...'):
                # 加载股票数据
                data, stock_code = data_loader.load_stock_data(selected_stock)
                
                if not data.empty:
                    # 添加技术指标
                    data = TechnicalIndicators.add_all_indicators(data)
                    
                    # 计算风险指标
                    risk_metrics = RiskMetrics.calculate_all_metrics(data)
                    
                    # 显示风险指标
                    st.subheader("风险指标")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("波动率", f"{format_number(risk_metrics['波动率']*100)}%")
                    with col2:
                        st.metric("夏普比率", format_number(risk_metrics['夏普比率']))
                    with col3:
                        st.metric("最大回撤", f"{format_number(risk_metrics['最大回撤']*100)}%")
                    
                    # 生成并显示交易建议
                    st.subheader("交易建议")
                    trading_suggestion = TechnicalIndicators.generate_trading_suggestion(data)
                    
                    # 显示建议和信号强度
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        # 根据建议设置不同的颜色
                        suggestion_color = {
                            "买入": "green",
                            "卖出": "red",
                            "观望": "blue"
                        }.get(trading_suggestion["建议操作"], "black")
                        
                        st.markdown(f"<h3 style='color: {suggestion_color}; text-align: center;'>"
                                  f"建议操作: {trading_suggestion['建议操作']}</h3>", 
                                  unsafe_allow_html=True)
                    with col2:
                        st.metric("信号强度", trading_suggestion["信号强度"])
                    
                    # 显示具体信号
                    st.subheader("技术信号详情")
                    for signal in trading_suggestion["具体信号"]:
                        st.write(f"• {signal}")
                    
                    # 创建并显示技术分析图表
                    st.subheader("技术分析图表")
                    charts = StockCharts()
                    fig = charts.create_stock_figure(data)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # 显示统计指标
                    st.subheader("统计指标")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        latest_close = data['Close'].iloc[-1]
                        prev_close = data['Close'].iloc[-2]
                        price_change = (latest_close - prev_close) / prev_close * 100
                        st.metric("最新收盘价", 
                                f"¥{format_number(latest_close)}", 
                                f"{format_number(price_change)}%")
                    with col2:
                        avg_volume = data['Volume'].mean()
                        volume_change = (data['Volume'].iloc[-1] - avg_volume) / avg_volume * 100
                        st.metric("平均成交量", 
                                format_number(avg_volume), 
                                f"{format_number(volume_change)}%")
                    with col3:
                        st.metric("RSI(14)", 
                                format_number(data['RSI'].iloc[-1]))
                    with col4:
                        price_range = f"¥{format_number(data['Low'].min())} - ¥{format_number(data['High'].max())}"
                        st.metric("价格区间", price_range)
                    
                    # 显示数据表格
                    st.subheader("历史数据")
                    st.dataframe(
                        data.sort_values('Date', ascending=False)
                            .style.format({
                                'Open': '{:.2f}',
                                'High': '{:.2f}',
                                'Low': '{:.2f}',
                                'Close': '{:.2f}',
                                'Volume': '{:,.0f}',
                                'RSI': '{:.2f}',
                                'MA5': '{:.2f}',
                                'MA20': '{:.2f}',
                                'MA60': '{:.2f}',
                                'MACD': '{:.2f}',
                                'Signal': '{:.2f}',
                                'MACD_hist': '{:.2f}'
                            })
                    )
                    
                    # 添加下载按钮
                    csv = data.to_csv(index=False)
                    st.download_button(
                        label="下载数据",
                        data=csv,
                        file_name=f'{stock_code}_data.csv',
                        mime='text/csv'
                    )
                else:
                    st.error("无法加载股票数据")

    except Exception as e:
        st.error(f"程序运行出错: {str(e)}")
        st.error(f"详细错误信息: {sys.exc_info()}")

if __name__ == '__main__':
    main()