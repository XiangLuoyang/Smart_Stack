import pandas as pd
import plotly.graph_objects as go
import streamlit as st

class StockCharts:
    """现代科技风格图表生成类"""
    
    COLORS = {
        'ma5': '#00bcd4',             # 短期均线（青色）
        'ma20': '#7c4dff',            # 长期均线（紫色）
        'up': '#00c853',              # 上涨（绿色）
        'down': '#ff5252'             # 下跌（红色）
    }

    @staticmethod
    def create_stock_figure(data: pd.DataFrame):
        try:
            fig = go.Figure()

            # 添加K线图
            fig.add_trace(
                go.Candlestick(
                    x=data['Date'],
                    open=data['Open'],
                    high=data['High'],
                    low=data['Low'],
                    close=data['Close'],
                    name='价格',
                    increasing_line_color=StockCharts.COLORS['up'],
                    decreasing_line_color=StockCharts.COLORS['down'],
                    text=[f'开盘: ¥{open:.2f}<br>'
                          f'最高: ¥{high:.2f}<br>'
                          f'最低: ¥{low:.2f}<br>'
                          f'收盘: ¥{close:.2f}'
                          for open, high, low, close in zip(data['Open'], 
                                                          data['High'], 
                                                          data['Low'], 
                                                          data['Close'])],
                    hoverinfo='text+x'
                )
            )

            # 添加移动平均线
            if 'MA5' in data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=data['Date'],
                        y=data['MA5'],
                        name='MA5',
                        line=dict(
                            color=StockCharts.COLORS['ma5'],
                            width=1.5
                        ),
                        text=[f'MA5: ¥{val:.2f}' for val in data['MA5']],
                        hoverinfo='text+x'
                    )
                )

            if 'MA20' in data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=data['Date'],
                        y=data['MA20'],
                        name='MA20',
                        line=dict(
                            color=StockCharts.COLORS['ma20'],
                            width=1.5
                        ),
                        text=[f'MA20: ¥{val:.2f}' for val in data['MA20']],
                        hoverinfo='text+x'
                    )
                )

            # 更新布局
            fig.update_layout(
                # 设置图表大小和边距
                height=600,
                margin=dict(
                    l=50,    # 左边距
                    r=50,    # 右边距
                    t=100,   # 上边距，为标题和图例留出空间
                    b=50     # 下边距
                ),
                
                # 标题设置
                title=dict(
                    text="股票走势分析",
                    font=dict(
                        size=24,
                        color='#2c3e50'
                    ),
                    x=0.5,          # 标题水平居中
                    y=0.95,         # 标题垂直位置
                    xanchor='center',
                    yanchor='top'
                ),
                
                # 图例设置
                showlegend=True,
                legend=dict(
                    orientation="h",     # 水平放置
                    yanchor="bottom",
                    y=1.02,             # 位置略微调整
                    xanchor="center",
                    x=0.5,
                    font=dict(
                        size=12,
                        color='#2c3e50'
                    ),
                    bgcolor='rgba(255,255,255,0.8)',  # 半透明背景
                    bordercolor='#E2E2E2',           # 边框颜色
                    borderwidth=1                     # 边框宽度
                ),
                
                # 背景颜色
                paper_bgcolor='white',
                plot_bgcolor='white',
                
                # 字体设置
                font=dict(
                    family="Arial, sans-serif",
                    size=12,
                    color='#2c3e50'
                ),
                
                # 悬停框样式
                hoverlabel=dict(
                    bgcolor='white',
                    font_size=12,
                    font_family="Arial, sans-serif",
                    bordercolor='#e0e0e0'
                ),
                
                # 禁用工具栏
                modebar_remove=['all']
            )

            # 更新X轴
            fig.update_xaxes(
                title_text="日期",
                title_font=dict(size=14, color='#2c3e50'),
                tickfont=dict(size=12, color='#2c3e50'),
                gridcolor='#e0e0e0',
                linecolor='#2c3e50',
                showgrid=True,
                rangeslider=dict(visible=False)  # 移除下方的滑动条
            )

            # 更新Y轴
            fig.update_yaxes(
                title_text="价格",
                title_font=dict(size=14, color='#2c3e50'),
                tickfont=dict(size=12, color='#2c3e50'),
                gridcolor='#e0e0e0',
                linecolor='#2c3e50',
                showgrid=True,
                side='left'        # Y轴显示在左侧
            )

            return fig

        except Exception as e:
            st.error(f"创建图表时出错: {str(e)}")
            return None