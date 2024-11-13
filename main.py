import os
import sys
import streamlit as st
import logging

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.config.settings import AppConfig
from src.data.loader import StockDataLoader
from src.models.technical import TechnicalIndicators
from src.models.risk import RiskMetrics
from src.visualization.charts import StockCharts
from src.utils.helpers import format_number
from src.models.prediction import EnhancedPrediction

# 设置日志配置
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

class EnhancedPrediction:
    # ...existing code...
    
    def feature_engineering(self, data):
        # 添加特征工程逻辑
        # 例如：计算移动平均线、技术指标等
        data['MA5'] = data['Close'].rolling(window=5).mean()
        data['MA20'] = data['Close'].rolling(window=20).mean()
        data['MA50'] = data['Close'].rolling(window=50).mean()
        data['MA60'] = data['Close'].rolling(window=60).mean()
        # ...其他特征工程逻辑...
        return data
    
    def ensemble_predict(self, data):
        # 添加预测逻辑
        # 例如：使用多个模型进行预测并计算加权平均值
        predictions = data['Close'] * 1.02  # 示例预测逻辑
        predictions.index = data.index  # 确保 predictions 有索引
        confidence = 0.95  # 示例置信度
        model_weights = {'model1': 0.5, 'model2': 0.5}  # 示例模型权重
        return {
            'predictions': predictions,
            'confidence': confidence,
            'model_weights': model_weights
        }
    
    def generate_signals(self, current_price, predicted_price):
        # 添加生成交易信号的逻辑
        if predicted_price > current_price * 1.05:
            action = 'Strong Buy'
        elif predicted_price > current_price:
            action = 'Buy'
        elif predicted_price < current_price * 0.95:
            action = 'Strong Sell'
        elif predicted_price < current_price:
            action = 'Sell'
        else:
            action = 'Hold'
        
        return {
            'action': action,
            'trend_analysis': '示例趋势分析',
            'technical_analysis': '示例技术分析',
            'risk_assessment': '示例风险评估',
            'recommendation': '示例建议操作'
        }
    
    def plot_prediction(self, actual_prices, predicted_prices):
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=actual_prices.index, y=actual_prices, mode='lines', name='实际价格'))
        fig.add_trace(go.Scatter(x=predicted_prices.index, y=predicted_prices, mode='lines', name='预测价格'))
        fig.update_layout(title='股票价格预测', xaxis_title='日期', yaxis_title='价格')
        return fig

def main():
    try:
        # 设置页面配置
        st.set_page_config(**AppConfig.PAGE_CONFIG)
        st.title(AppConfig.TITLE)

        # ���边栏配置
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
                
                if data.empty:
                    st.error(f"没有找到股票数据: {selected_stock}")
                    return
                
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
                            'MA50': '{:.2f}',  # Add MA50
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
                
                # 预测分析部分
                if data is not None:
                    # Verify columns exist
                    required_columns = ['MA5', 'MA20', 'MA50', 'MA60', 'RSI', 'MACD', 'Signal', 'MACD_hist']
                    missing_columns = [col for col in required_columns if col not in data.columns]
                    
                    if missing_columns:
                        st.error(f"Missing required columns: {', '.join(missing_columns)}")
                        return
                    
                    st.subheader("预测分析")
                    
                    try:
                        if data is not None and not data.empty:
                            # 创建预测模型实例
                            predictor = EnhancedPrediction()
                            
                            # 特征工程
                            features_df = predictor.feature_engineering(data.copy())
                            
                            # 获取预测结果
                            results = predictor.ensemble_predict(data.copy())
                            st.write(f"预测置信度: {results['confidence']:.2%}")
                            st.write("模型权重:", results['model_weights'])
                            pred_price = results['predictions']
                            
                            # 显示预测结果
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.metric(
                                    "5日后预测价格",
                                    f"¥{pred_price.iloc[-1]:.2f}",
                                    f"{((pred_price.iloc[-1] - data['Close'].iloc[-1]) / data['Close'].iloc[-1] * 100):.2f}%"
                                )
                            
                            # 生成交易信号
                            signals = predictor.generate_signals(data['Close'].iloc[-1], pred_price.iloc[-1])
                            
                            with col2:
                                signal_color = {
                                    'Strong Buy': 'green',
                                    'Buy': 'lightgreen',
                                    'Hold': 'gray',
                                    'Sell': 'orange',
                                    'Strong Sell': 'red'
                                }
                                st.markdown(
                                    f"**交易信号:** ::{signal_color[signals['action']]}[{signals['action']}]"
                                )
                            
                            # 展示分析依据
                            st.markdown("### 分析依据")
                            st.markdown(f"""
                            - 趋势分析: {signals['trend_analysis']}
                            - 技术指标: {signals['technical_analysis']}
                            - 风险评估: {signals['risk_assessment']}
                            - 建议操作: {signals['recommendation']}
                            """)
                            
                            # 绘制预测走势图
                            fig = predictor.plot_prediction(data['Close'], pred_price)
                            st.plotly_chart(fig)
                    except Exception as e:
                        logging.error("预测过程出错", exc_info=True)
                        st.error(f"预测过程出错: {str(e)}")
    except Exception as e:
        logging.error("程序运行出���", exc_info=True)
        st.error(f"程序运行出错: {str(e)}")
        st.exception(e)  # This will show the full traceback

if __name__ == '__main__':
    main()