import streamlit as st
from datetime import date, datetime
import yfinance as yf
from prophet import Prophet
from prophet.plot import plot_plotly
from plotly import graph_objs as go
import pandas as pd
from statistics import mean

# 获取所有可交易的股票代码
try:
    import yfinance as yf
    all_stocks = yf.Ticker('^GSPC').symbols  # 使用 S&P 500 指数获取一些常见股票代码
except:
    all_stocks = []

START = "2015-01-01"
TODAY = date.today().strftime("%Y-%m-%d")

st.title('股票预测应用')

# 股票代码输入框，支持自动匹配
selected_stock = st.text_input('请输入股票代码', placeholder='例如：AAPL 或 00700.HK', autocomplete='off')

# 匹配股票代码
if selected_stock:
    matching_stocks = [stock for stock in all_stocks if selected_stock.upper() in stock]
    if matching_stocks:
        st.write("猜你想选：", ", ".join(matching_stocks))

# 修改为预测月数
n_months = st.slider('预测月数', 1, 48, step=1)
period = n_months * 30  # 简单地将月数转换为天数

start_date = st.date_input('选择预测的开始日期', value=datetime(2020, 1, 1), min_value=datetime(2015, 1, 1), max_value=date.today())

@st.cache_data
def load_data(ticker):
    data = yf.download(ticker, START, TODAY)
    data.reset_index(inplace=True)
    return data

if selected_stock:
    # 加载数据
    data_load_state = st.text('加载数据...')
    try:
        data = load_data(selected_stock)
        data_load_state.text('加载数据...完成!')

        st.subheader('原始数据')
        data_renamed = data.rename(columns={
            'Date': '日期',
            'Open': '开盘价',
            'High': '最高价',
            'Low': '最低价',
            'Close': '收盘价',
            'Adj Close': '调整后收盘价',
            'Volume': '成交量'
        })
        st.write(data_renamed.tail())

        def plot_raw_data():
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=data_renamed['日期'], y=data_renamed['开盘价'], name="开盘价"))
            fig.add_trace(go.Scatter(x=data_renamed['日期'], y=data_renamed['收盘价'], name="收盘价"))
            fig.layout.update(title_text='带有范围滑动条的时间序列数据', xaxis_rangeslider_visible=True)
            st.plotly_chart(fig)

        plot_raw_data()

        filtered_data = data_renamed[data_renamed['日期'] >= str(start_date)]

        df_train = filtered_data[['日期', '收盘价']].rename(columns={"日期": "ds", "收盘价": "y"})

        try:
            m = Prophet()
            m.fit(df_train)
            future = m.make_future_dataframe(periods=period)
            forecast = m.predict(future)

            forecast_renamed = forecast.rename(columns={
                'ds': '日期',
                'yhat': '预测值',
                'yhat_lower': '预测值下限',
                'yhat_upper': '预测值上限',
                'trend': '趋势',
                'trend_lower': '趋势下限',
                'trend_upper': '趋势上限',
                'additive_terms': '加性项',
                'additive_terms_lower': '加性项下限',
                'additive_terms_upper': '加性项上限',
                'daily': '日度',
                'daily_lower': '日度下限',
                'daily_upper': '日度上限',
                'weekly': '周度',
                'weekly_lower': '周度下限',
                'weekly_upper': '周度上限',
                'yearly': '年度',
                'yearly_lower': '年度下限',
                'yearly_upper': '年度上限',
                'multiplicative_terms': '乘法项',
                'multiplicative_terms_lower': '乘法项下限',
                'multiplicative_terms_upper': '乘法项上限',
            })

            st.subheader('预测数据')
            st.write(forecast_renamed[['日期', '预测值', '预测值下限', '预测值上限', '趋势', '趋势下限', '趋势上限']].tail())

            st.write(f'未来 {n_months} 个月的预测图')  # 修改为月数
            fig1 = plot_plotly(m, forecast)
            st.plotly_chart(fig1)

            st.write("预测与实际对比")
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=filtered_data['日期'], y=filtered_data['收盘价'], name="实际"))
            fig2.add_trace(go.Scatter(x=forecast_renamed['日期'], y=forecast_renamed['预测值'], name="预测"))
            fig2.layout.update(title_text='预测与实际对比', xaxis_rangeslider_visible=True)
            st.plotly_chart(fig2)
            
            st.write("预测组件")
            
            components_df = pd.concat([forecast[['ds']], forecast.drop(columns=['ds'])], axis=1)
            components_renamed = components_df.rename(columns={
                'ds': '日期',
                'trend': '趋势',
                'trend_lower': '趋势下限',
                'trend_upper': '趋势上限',
                'additive_terms': '加性项',
                'additive_terms_lower': '加性项下限',
                'additive_terms_upper': '加性项上限',
                'daily': '日度',
                'daily_lower': '日度下限',
                'daily_upper': '日度上限',
                'weekly': '周度',
                'weekly_lower': '周度下限',
                'weekly_upper': '周度上限',
                'yearly': '年度',
                'yearly_lower': '年度下限',
                'yearly_upper': '年度上限',
                'multiplicative_terms': '乘法项',
                'multiplicative_terms_lower': '乘法项下限',
                'multiplicative_terms_upper': '乘法项上限',
            })

            st.write(components_renamed.tail())
            
            # 业务解读和买入意见
            st.subheader('业务解读和买入意见')

            # 基于预测数据的业务解读
            last_actual_price = filtered_data['收盘价'].iloc[-1]
            future_prices = forecast['yhat'].tail(period)
            mean_future_price = mean(future_prices)

            if mean_future_price > last_actual_price:
                buy_opinion = "未来趋势看涨，建议考虑买入。"
            else:
                buy_opinion = "未来趋势为下行或持平，建议谨慎操作。"

            business_analysis = f"""
            ### 当前情况
            - 当前股票代码：{selected_stock}
            - 当前日期：{filtered_data['日期'].iloc[-1].strftime('%Y-%m-%d')}
            - 当前收盘价：{last_actual_price:.2f} 元
            - 预测开始日期：{str(start_date)}

            ### 未来趋势预测
            - 未来 {n_months} 个月内平均预测值：{mean_future_price:.2f} 元  # 修改为月数
            - 当前价格与未来预测平均价格之比：{mean_future_price / last_actual_price:.2f}

            ### 综合分析
            {buy_opinion}
            """

            st.markdown(business_analysis)

        except Exception as e:
            st.error(f"预测时出错: {e}")

    except:
        st.error("加载股票数据失败，请检查股票代码是否正确。")
