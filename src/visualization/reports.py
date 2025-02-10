import pandas as pd
from typing import Dict
import streamlit as st

class ReportGenerator:
    def generate_analysis_report(
        self,
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
