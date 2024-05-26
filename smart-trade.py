import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date, datetime

from prophet import Prophet
from prophet.plot import plot_plotly
from plotly import graph_objects as go
from numpy import mean

# --- 页面配置 ---
st.set_page_config(layout="wide")

# --- 标题 ---
st.title("📈 股票预测应用")

# --- 默认值 ---
START = "2015-01-01"
TODAY = date.today().strftime("%Y-%m-%d")

# --- 用户输入 ---
st.sidebar.header("股票代码")
selected_stock = st.sidebar.text_input("输入股票代码 (例如: AAPL)", "AAPL")

# --- 参数设置 ---
st.sidebar.header("预测参数")
n_months = st.sidebar.slider("预测月数:", 1, 36, 12)
period = n_months * 30

# --- 数据加载 ---
@st.cache_data
def load_data(ticker):
    data = yf.download(ticker, START, TODAY)
    data.reset_index(inplace=True)
    return data


# --- 主要内容区域 ---
if selected_stock:
    # --- 加载数据 ---
    data_load_state = st.text("加载数据...")
    try:
        data = load_data(selected_stock)
        data_load_state.text("加载数据...完成!")

        # --- 数据展示 ---
        data_renamed = data.rename(
            columns={
                "Date": "日期",
                "Open": "开盘价",
                "High": "最高价",
                "Low": "最低价",
                "Close": "收盘价",
                "Adj Close": "调整后收盘价",
                "Volume": "成交量",
            }
        )

        # --- 原始数据 ---
        st.subheader("原始数据")
        st.write(data_renamed.tail())

        st.plotly_chart(
            go.Figure()
            .add_trace(
                go.Scatter(
                    x=data_renamed["日期"],
                    y=data_renamed["开盘价"],
                    name="开盘价",
                )
            )
            .add_trace(
                go.Scatter(
                    x=data_renamed["日期"],
                    y=data_renamed["收盘价"],
                    name="收盘价",
                )
            )
            .update_layout(
                title_text="带有范围滑动条的时间序列数据",
                xaxis_rangeslider_visible=True,
            ),
            use_container_width=True,
        )

        # --- 数据预处理 ---
        start_date = st.date_input(
            "选择预测的开始日期",
            value=datetime(2020, 1, 1),
            min_value=datetime(2015, 1, 1),
            max_value=date.today(),
        )
        filtered_data = data_renamed[data_renamed["日期"] >= str(start_date)]
        df_train = filtered_data[["日期", "收盘价"]].rename(
            columns={"日期": "ds", "收盘价": "y"}
        )

        # --- 模型训练和预测 ---
        try:
            m = Prophet()
            m.fit(df_train)
            future = m.make_future_dataframe(periods=period)
            forecast = m.predict(future)

            # --- 结果展示 ---
            forecast_renamed = forecast.rename(
                columns={
                    "ds": "日期",
                    "yhat": "预测值",
                    "yhat_lower": "预测值下限",
                    "yhat_upper": "预测值上限",
                    "trend": "趋势",
                    "trend_lower": "趋势下限",
                    "trend_upper": "趋势上限",
                }
            )

            # --- 预测数据 ---
            st.subheader("预测数据")
            st.write(forecast_renamed[
                    [
                        "日期",
                        "预测值",
                        "预测值下限",
                        "预测值上限",
                        "趋势",
                        "趋势下限",
                        "趋势上限",
                    ]
                ].tail())
            
            st.plotly_chart(
                plot_plotly(m, forecast), use_container_width=True
            )

            # --- 预测组件 ---
            components_df = pd.concat(
                [forecast[["ds"]], forecast.drop(columns=["ds"])], axis=1
            )
            components_renamed = components_df.rename(
                columns={
                    "ds": "日期",
                    "trend": "趋势",
                    "trend_lower": "趋势下限",
                    "trend_upper": "趋势上限",
                    "additive_terms": "加性项",
                    "additive_terms_lower": "加性项下限",
                    "additive_terms_upper": "加性项上限",
                    "daily": "日度",
                    "daily_lower": "日度下限",
                    "daily_upper": "日度上限",
                    "weekly": "周度",
                    "weekly_lower": "周度下限",
                    "weekly_upper": "周度上限",
                    "yearly": "年度",
                    "yearly_lower": "年度下限",
                    "yearly_upper": "年度上限",
                    "multiplicative_terms": "乘法项",
                    "multiplicative_terms_lower": "乘法项下限",
                    "multiplicative_terms_upper": "乘法项上限",
                }
            )
            
            st.subheader("预测组件")
            st.write(components_renamed.tail())

            st.plotly_chart(
                go.Figure()
                .add_trace(
                    go.Scatter(
                        x=filtered_data["日期"],
                        y=filtered_data["收盘价"],
                        name="实际",
                    )
                )
                .add_trace(
                    go.Scatter(
                        x=forecast_renamed["日期"],
                        y=forecast_renamed["预测值"],
                        name="预测",
                    )
                )
                .update_layout(
                    title_text="预测与实际对比",
                    xaxis_rangeslider_visible=True,
                ),
                use_container_width=True,
            )

            # --- 业务解读和买入意见 ---
            st.subheader("业务解读和买入意见")

            # --- 基于预测数据的业务解读 ---
            last_actual_price = filtered_data["收盘价"].iloc[-1]
            future_prices = forecast["yhat"].tail(period)
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
            - 未来 {n_months} 个月内平均预测值：{mean_future_price:.2f} 元
            - 当前价格与未来预测平均价格之比：{mean_future_price / last_actual_price:.2f}

            ### 综合分析
            {buy_opinion}
            """

            st.markdown(business_analysis)

        except Exception as e:
            st.write(f"Prophet 模型预测出错: {e}")
    except Exception as e:
        data_load_state.text(f"加载数据...出错: {e}")
