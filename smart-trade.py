import streamlit as st  
import yfinance as yf  
import pandas as pd  
import numpy as np  
from datetime import datetime, date, timedelta  
from typing import Dict, List, Tuple  
import plotly.graph_objects as go  
from plotly.subplots import make_subplots  
from scipy import stats  

# 设置页面配置  
st.set_page_config(  
    page_title="股票数据分析与预测系统",  
    page_icon="📈",  
    layout="wide"  
)  

def get_sz100_tickers() -> List[str]:  
    """从本地CSV文件获取深证100指数成分股列表"""  
    try:  
        # 读取存储股票代码的CSV文件，列名为'code'  
        df = pd.read_csv('sz100_tickers.csv')  
        
        # 将股票代码转换为列表  
        tickers = df['code'].tolist()  
        return tickers  
    except Exception as e:  
        st.error(f"读取股票列表失败: {str(e)}")  
        return []  

def load_data(ticker: str) -> Tuple[pd.DataFrame, str]:  
    """使用yfinance加载股票数据"""  
    try:  
        stock = yf.Ticker(ticker)  
        data = stock.history(period="2y")  
        
        if data.empty:  
            return pd.DataFrame(), ticker  
        
        # 重置索引，将日期变成列  
        data.reset_index(inplace=True)  
        
        # 使用股票代码作为股票名称  
        stock_name = ticker  
        
        return data, stock_name  
        
    except Exception as e:  
        st.error(f"加载数据失败: {str(e)}")  
        return pd.DataFrame(), ''  

def add_technical_indicators(data: pd.DataFrame) -> pd.DataFrame:  
    """添加技术指标"""  
    try:  
        # 计算移动平均线  
        data['MA5'] = data['Close'].rolling(window=5).mean()  
        data['MA20'] = data['Close'].rolling(window=20).mean()  
        data['MA60'] = data['Close'].rolling(window=60).mean()  
        
        # 计算RSI  
        delta = data['Close'].diff()  
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()  
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()  
        rs = gain / loss  
        data['RSI'] = 100 - (100 / (1 + rs))  
        
        # 计算MACD  
        exp1 = data['Close'].ewm(span=12, adjust=False).mean()  
        exp2 = data['Close'].ewm(span=26, adjust=False).mean()  
        data['MACD'] = exp1 - exp2  
        data['Signal_Line'] = data['MACD'].ewm(span=9, adjust=False).mean()  
        data['MACD_Histogram'] = data['MACD'] - data['Signal_Line']  
        
        return data  
    except Exception as e:  
        st.error(f"计算技术指标时出错: {str(e)}")  
        return data  

def calculate_risk_metrics(data: pd.DataFrame) -> Dict[str, float]:  
    """计算风险指标"""  
    try:  
        # 计算日收益率  
        returns = data['Close'].pct_change().dropna()  
        
        # 计算年化波动率  
        volatility = returns.std() * np.sqrt(252) * 100  
        
        # 计算最大回撤  
        cumulative_returns = (1 + returns).cumprod()  
        rolling_max = cumulative_returns.expanding().max()  
        drawdowns = (cumulative_returns - rolling_max) / rolling_max  
        max_drawdown = drawdowns.min() * 100  
        
        # 计算夏普比率 (假设无风险利率为3%)  
        risk_free_rate = 0.03  
        excess_returns = returns.mean() * 252 - risk_free_rate  
        sharpe_ratio = excess_returns / (returns.std() * np.sqrt(252))  
        
        return {  
            '波动率': volatility,  
            '最大回撤': abs(max_drawdown),  
            '夏普比率': sharpe_ratio  
        }  
    except Exception as e:  
        st.error(f"计算风险指标时出错: {str(e)}")  
        return {  
            '波动率': 0.0,  
            '最大回撤': 0.0,  
            '夏普比率': 0.0  
        }  

def calculate_expected_return(  
    ticker: str,  
    start_date: datetime,  
    days: int,  
    confidence: float  
) -> Dict[str, float]:  
    """计算预期收益率和置信区间"""  
    try:  
        # 获取历史数据  
        stock = yf.Ticker(ticker)  
        hist_data = stock.history(start=start_date)  
        
        if hist_data.empty:  
            return {'error': '无法获取历史数据'}  
        
        # 计算历史日收益率  
        returns = hist_data['Close'].pct_change().dropna()  
        
        # 计算预期收益率（年化）  
        exp_return = returns.mean() * 252 * 100  
        
        # 计算收益率的标准差  
        std_dev = returns.std() * np.sqrt(252)  
        
        # 计算置信区间  
        z_score = stats.norm.ppf((1 + confidence) / 2)  
        margin_of_error = z_score * std_dev * 100  
        
        return {  
            'expected_return': exp_return,  
            'lower_bound': exp_return - margin_of_error,  
            'upper_bound': exp_return + margin_of_error,  
            'forecast': hist_data['Close'].iloc[-days:].values  
        }  
    except Exception as e:  
        return {'error': str(e)}  

def plot_stock_analysis(data: pd.DataFrame, forecast: np.ndarray):  
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
            template='plotly_dark',  
            height=800  
        )  

        # 显示图表  
        st.plotly_chart(fig, use_container_width=True)  

    except Exception as e:  
        st.error(f"绘制图表时出错: {str(e)}")  

def generate_analysis_report(  
    stock_data: pd.DataFrame,  
    risk_metrics: Dict[str, float],  
    prediction_results: Dict[str, float]  
) -> None:  
    """生成分析报告"""  
    try:  
        st.subheader("📊 分析报告")  
        
        # 使用表格样式显示详细数据  
        st.markdown("### 📈 核心指标")  
        
        # 创建详细的分析数据表格  
        data = {  
            '指标类别': ['预测指标', '预测指标', '预测指标', '风险指标', '风险指标', '风险指标'],  
            '指标名称': [  
                '预期收益率',  
                '预测下界',  
                '预测上界',  
                '波动率',  
                '最大回撤',  
                '夏普比率'  
            ],  
            '数值': [  
                f"{prediction_results['expected_return']:.2f}%",  
                f"{prediction_results['lower_bound']:.2f}%",  
                f"{prediction_results['upper_bound']:.2f}%",  
                f"{risk_metrics['波动率']:.2f}%",  
                f"{risk_metrics['最大回撤']:.2f}%",  
                f"{risk_metrics['夏普比率']:.2f}"  
            ]  
        }  
        
        df_report = pd.DataFrame(data)  
        st.dataframe(  
            df_report,  
            column_config={  
                "指标类别": st.column_config.TextColumn("指标类别", width=100),  
                "指标名称": st.column_config.TextColumn("指标名称", width=100),  
                "数值": st.column_config.TextColumn("数值", width=100),  
            },  
            hide_index=True,  
        )  
        
        # 投资建议  
        st.markdown("### 💡 投资建议")  
        
        expected_return = prediction_results['expected_return']  
        if expected_return > 10:  
            st.success("📈 强烈推荐买入 ⭐⭐⭐")  
            st.markdown("""  
                - 预期收益率表现优异  
                - 技术指标呈现强势上涨趋势  
                - 建议：可以考虑建仓或加仓  
            """)  
        elif expected_return > 5:  
            st.info("📊 建议考虑买入 ⭐⭐")  
            st.markdown("""  
                - 预期收益率表现良好  
                - 技术指标呈现稳定上涨趋势  
                - 建议：可以小仓位试探性建仓  
            """)  
        elif expected_return > 0:  
            st.warning("📉 建议持有观望 ⭐")  
            st.markdown("""  
                - 预期收益率表现一般  
                - 技术指标呈现震荡趋势  
                - 建议：观望为主，等待更好的入场机会  
            """)  
        else:  
            st.error("⚠️ 建议回避 ❌")  
            st.markdown("""  
                - 预期收益率表现不佳  
                - 技术指标呈现下跌趋势  
                - 建议：暂时避险，注意风险控制  
            """)  
            
        # 添加风险提示  
        st.markdown("### ⚠️ 风险提示")  
        st.markdown("""  
        - 以上分析仅供参考，不构成投资建议  
        - 股市有风险，投资需谨慎  
        - 过往表现不代表未来收益  
        - 建议投资者根据自身风险承受能力做出投资决策  
        """)  
        
    except Exception as e:  
        st.error(f"生成分析报告时出错: {str(e)}")  

def main():  
    try:  
        st.title("📈 股票数据分析与预测系统")  
        
        # 侧边栏配置  
        with st.sidebar:  
            st.header("配置参数")  
            tickers = get_sz100_tickers()  
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

        if selected_stock:  
            with st.spinner('正在加载数据...'):  
                # 加载和处理数据  
                data, stock_name = load_data(selected_stock)  
                
                if data.empty:  
                    st.error("无法加载股票数据，请检查股票代码是否正确")  
                    return  
                    
                # 确保日期格式正确，并移除时区信息  
                data['Date'] = pd.to_datetime(data['Date']).dt.tz_localize(None)  
                
                try:  
                    # 添加技术指标  
                    data = add_technical_indicators(data)  
                    
                    # 计算风险指标  
                    risk_metrics = calculate_risk_metrics(data)  
                    
                    # 计算预期收益率  
                    prediction_results = calculate_expected_return(  
                        selected_stock,  
                        start_date,  
                        period,  
                        confidence_interval  
                    )  
                    
                    if prediction_results.get('error'):  
                        st.error(f"预测过程出错: {prediction_results['error']}")  
                        return  
                    
                    # 展示图表  
                    plot_stock_analysis(data, prediction_results['forecast'])  
                    
                    # 生成分析报告  
                    generate_analysis_report(data, risk_metrics, prediction_results)  
                    
                except Exception as e:  
                    st.error(f"处理数据时发生错误: {str(e)}")  
        else:  
            st.info("👈 请在侧边栏选择一个股票代码开始分析")  
            
    except Exception as e:  
        st.error(f"程序运行出错: {str(e)}")  

if __name__ == '__main__':  
    main()