import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.config.settings import ChartConfig
import streamlit as st
import numpy as np

class ChartGenerator:
    def __init__(self, chart_config: ChartConfig):
        self.chart_config = chart_config

    def plot_stock_analysis(self, data: pd.DataFrame, forecast: np.ndarray):
        """绘制股票分析图表"""
        try:
            # 创建子图
            fig = make_subplots(
                rows=3, 
                cols=1,
                row_heights=[0.5, 0.25, 0.25],
                subplot_titles=('价格走势', '成交量', '技术指标'),
                vertical_spacing=0.1
            )

            # 添加K线图
            fig.add_trace(
                go.Candlestick(
                    x=data['Date'],
                    open=data['Open'],
                    high=data['High'],
                    low=data['Low'],
                    close=data['Close'],
                    name='K线'
                ),
                row=1, col=1
            )

            # 添加移动平均线
            fig.add_trace(
                go.Scatter(
                    x=data['Date'],
                    y=data['MA5'],
                    name='MA5',
                    line=dict(color='orange')
                ),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=data['Date'],
                    y=data['MA20'],
                    name='MA20',
                    line=dict(color='blue')
                ),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=data['Date'],
                    y=data['MA60'],
                    name='MA60',
                    line=dict(color='purple')
                ),
                row=1, col=1
            )

            # 添加成交量图
            fig.add_trace(
                go.Bar(
                    x=data['Date'],
                    y=data['Volume'],
                    name='成交量'
                ),
                row=2, col=1
            )

            # 添加RSI指标
            fig.add_trace(
                go.Scatter(
                    x=data['Date'],
                    y=data['RSI'],
                    name='RSI'
                ),
                row=3, col=1
            )

            # 更新布局
            fig.update_layout(
                title='股票分析图表',
                xaxis_title='日期',
                yaxis_title='价格',
                template=self.chart_config.template,
                height=self.chart_config.height
            )

            # 显示图表
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"绘制图表时出错: {str(e)}")
