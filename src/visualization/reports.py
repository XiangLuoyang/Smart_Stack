import pandas as pd
import streamlit as st
from typing import Dict

class ReportGenerator:
    """报告生成类"""
    
    @staticmethod
    def generate_summary(data: pd.DataFrame, risk_metrics: Dict[str, float]) -> None:
        """生成摘要报告"""
        # 计算基本统计数据
        latest_price = data['Close'].iloc[-1]
        price_change = (latest_price - data['Close'].iloc[-2]) / data['Close'].iloc[-2]
        avg_volume = data['Volume'].mean()
        
        # 显示统计信息
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "最新价",
                f"¥{latest_price:.2f}",
                f"{price_change:.2%}"
            )
            
        with col2:
            st.metric(
                "平均成交量",
                f"{avg_volume:,.0f}"
            )
            
        with col3:
            st.metric(
                "波动率",
                f"{risk_metrics['波动率']:.2%}"
            )
            
    @staticmethod
    def generate_technical_analysis(data: pd.DataFrame) -> None:
        """生成技术分析报告"""
        # 计算技术指标信号
        ma5 = data['MA5'].iloc[-1]
        ma20 = data['MA20'].iloc[-1]
        rsi = data['RSI'].iloc[-1]
        
        # 生成分析结论
        st.subheader("技术分析")
        
        # MA分析
        if ma5 > ma20:
            st.write("📈 MA5突破MA20，可能显示上升趋势")
        else:
            st.write("📉 MA5低于MA20，可能显示下降趋势")
            
        # RSI分析
        if rsi > 70:
            st.write("⚠️ RSI超买（{}），可能存在回调风险".format(round(rsi, 2)))
        elif rsi < 30:
            st.write("💡 RSI超卖（{}），可能存在反弹机会".format(round(rsi, 2)))
        else:
            st.write("➡️ RSI在中性区间（{}）".format(round(rsi, 2)))