import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta, date
from typing import List
from prophet import Prophet
# from prophet.plot import plot_plotly  # 如果不需要使用 Prophet 的绘图功能，可以删除此行
import pandas as pd
from statistics import mean
import plotly.graph_objects as go

# --- 函数定义 ---


@st.cache_data
def load_data(ticker: str):
    """从 Yahoo Finance 下载股票数据"""
    data = yf.download(ticker, period="max")
    data.reset_index(inplace=True)
    return data


@st.cache_data
def get_sz100_tickers() -> List[str]:
    """从 CSV 文件中读取深证100股票代码列表"""
    df = pd.read_csv("sz100_tickers.csv")
    tickers = df.iloc[:, 0].tolist()
    return tickers


def calculate_expected_return(ticker: str, start_date: datetime, period: int) -> float:
    """计算预期收益率"""
    try:
        data = load_data(ticker)

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

        filtered_data = data_renamed[data_renamed["日期"] >= str(start_date)]
        df_train = filtered_data[["日期", "收盘价"]].rename(
            columns={"日期": "ds", "收盘价": "y"}
        )
        m = Prophet()
        m.fit(df_train)
        future = m.make_future_dataframe(periods=period)
        forecast = m.predict(future)
        last_actual_price = filtered_data["收盘价"].iloc[-1]
        mean_future_price = mean(forecast["yhat"].tail(period))
        return (mean_future_price - last_actual_price) / last_actual_price * 100
    except Exception:
        return float("-inf")


# --- 页面配置 ---
st.set_page_config(page_title="股票数据分析", page_icon=":chart_with_upwards_trend:")
st.title("股票数据分析")

# --- 股票选择 ---
selected_stock = st.sidebar.selectbox("选择股票代码", get_sz100_tickers())

# --- 参数设置 ---
period = st.sidebar.slider("预测天数", min_value=1, max_value=365, value=30)
start_date = st.sidebar.date_input(
    "选择预测的开始日期",
    value=datetime(2020, 1, 1),
    min_value=datetime(2015, 1, 1),
    max_value=date.today(),
)

# --- 主要内容区域 ---
if selected_stock:
    # --- 加载数据 ---
    data_load_state = st.text("加载数据...")
    try:
        data = load_data(selected_stock)

        # --- 数据重命名 ---
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

        data_load_state.text("加载数据...完成!")

        # --- 数据展示 ---
        st.subheader("股票数据")
        st.write(data_renamed.tail(10))

        # --- 数据预处理 ---
        filtered_data = data_renamed[data_renamed["日期"] >= str(start_date)]
        df_train = filtered_data[["日期", "收盘价"]].rename(
            columns={"日期": "ds", "收盘价": "y"}
        )

        # --- 模型训练和预测 ---
        m = Prophet()
        m.fit(df_train)
        future = m.make_future_dataframe(periods=period)
        forecast = m.predict(future)

        # --- 计算过去时间段的误差
        today = datetime.today()
        one_year_ago = today - timedelta(days=365)
        one_quarter_ago = today - timedelta(days=90)
        one_month_ago = today - timedelta(days=30)

        def calculate_error(start_date, end_date):
            mask = (forecast['ds'] >= start_date) & (forecast['ds'] <= end_date)
            forecast_period = forecast.loc[mask]
            actual_period = df_train.loc[df_train['ds'].isin(forecast_period['ds'])]
            error = ((forecast_period['yhat'] - actual_period['y']) / actual_period['y'] * 100).mean()
            return error

        one_year_error = calculate_error(one_year_ago, today)
        one_quarter_error = calculate_error(one_quarter_ago, today)
        one_month_error = calculate_error(one_month_ago, today)

        # ---  历史数据和预测可视化 ---
        st.subheader("历史数据及预测")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_train['ds'], y=df_train['y'], mode='lines', name='历史数据'))
        fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat'], mode='lines', name='预测数据'))
        fig.update_layout(title_text="股票价格走势", xaxis_title="日期", yaxis_title="收盘价")
        st.plotly_chart(fig)

        # --- 误差表格 ---
        st.subheader("预测误差")
        error_data = {
            "时间段": ["过去一年", "过去一个季度", "过去一个月"],
            "平均误差 (%)": [f"{one_year_error:.2f}", f"{one_quarter_error:.2f}", f"{one_month_error:.2f}"]
        }
        error_df = pd.DataFrame(error_data)
        st.table(error_df)

        # --- 业务解读和买入意见 ---
        st.subheader("业务解读和买入意见")
        st.write("根据以上分析，预测未来", period, "天", selected_stock, "的预期收益率为", "{:.2f}".format(calculate_expected_return(selected_stock, start_date, period)), "%。")
        # 这里可以根据模型预测的结果，结合股票的市场表现、行业趋势等因素，给出更具体的业务解读和买入建议。
        # 例如：
        if calculate_expected_return(selected_stock, start_date, period) > 5:
            st.write("该股票近期表现强势，预测未来收益可观，建议投资者关注买入机会。")
        elif calculate_expected_return(selected_stock, start_date, period) > 0:
            st.write("该股票未来收益相对稳定，可以考虑逢低买入。")
        else:
            st.write("该股票未来收益存在一定风险，建议投资者谨慎观望。")

        # --- 深证100股票预测 ---
        if st.button("开始预测深证100股票"):
            st.subheader("深证100股票预测")
            sz100_tickers = get_sz100_tickers()
            returns = []
            for ticker in sz100_tickers:
                expected_return = calculate_expected_return(ticker, start_date, period)
                returns.append({"股票代码": ticker, "预期收益率": expected_return})
            df_returns = pd.DataFrame(returns)
            top_10_stocks = df_returns.sort_values(by="预期收益率", ascending=False).head(10)
            st.write(top_10_stocks)

    except Exception as e:
        data_load_state.text(f"加载数据...出错: {e}")
