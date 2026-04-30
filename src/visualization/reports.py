import pandas as pd
from typing import Dict, Any 
import streamlit as st
import talib # Import TA-Lib for candlestick patterns
import traceback # Import traceback for detailed error logging

class ReportGenerator:
    def generate_analysis_report(
        self,
        stock_data: pd.DataFrame, 
        risk_metrics: Dict[str, Any], 
        prediction_results: Dict[str, Any]
    ) -> None:
        """生成分析报告"""
        try:
            # Check if prediction_results indicates an error.
            # This check should ideally be in smart-trade.py before calling this,
            # but an additional safeguard here is fine.
            if isinstance(prediction_results.get('error'), str):
                # If generate_analysis_report is called with an error dict,
                # it might be better to display nothing or just the error.
                # For now, this function will proceed, and .get(key, 'N/A') will handle missing data.
                pass # Or st.error(f"无法生成报告: {prediction_results['error']}") and return

            # Normalize prediction results keys
            # prediction.py returns raw decimals (e.g., 0.001); reports need percentages
            expected_ret_raw = prediction_results.get('expected_daily_return', None)
            daily_std_raw = prediction_results.get('daily_std', None)
            ci = prediction_results.get('confidence_interval', {}) or {}

            expected_daily_return_pct = (
                round(expected_ret_raw * 100, 4) if isinstance(expected_ret_raw, (int, float))
                else None
            )
            daily_volatility_pct = (
                round(daily_std_raw * 100, 4) if isinstance(daily_std_raw, (int, float))
                else None
            )
            daily_lower_bound_pct = (
                round(ci.get('lower', 0) * 100, 4) if ci else None
            )
            daily_upper_bound_pct = (
                round(ci.get('upper', 0) * 100, 4) if ci else None
            )

            # Section for Core Metrics
            st.markdown("### 📈 核心指标")
            core_metrics_data = {
                '指标类别': ['预测指标', '预测指标', '预测指标', '预测指标', '风险指标 (历史)', '风险指标 (历史)'],
                '指标名称': [
                    '预期日收益率', '预测日下界', '预测日上界', '预测日波动率',
                    '最大回撤', '夏普比率'
                ],
                '数值': [
                    expected_daily_return_pct,
                    daily_lower_bound_pct,
                    daily_upper_bound_pct,
                    daily_volatility_pct,
                    risk_metrics.get('最大回撤', None),
                    risk_metrics.get('夏普比率', None),
                ]
            }

            formatted_metric_values = []
            for val in core_metrics_data['数值']:
                if isinstance(val, (int, float)):
                    formatted_metric_values.append(f"{val:.2f}%")
                else:
                    formatted_metric_values.append(str(val) if val is not None else 'N/A')
            core_metrics_data['数值'] = formatted_metric_values

            df_core_metrics = pd.DataFrame(core_metrics_data)

            # Check if there's any meaningful data to display in the table
            has_predictive_data = expected_daily_return_pct is not None
            has_risk_data = (
                risk_metrics.get('最大回撤') is not None
                or risk_metrics.get('夏普比率') is not None
            )

            if has_predictive_data or has_risk_data:
                st.dataframe(
                    df_core_metrics,
                    column_config={
                        "指标类别": st.column_config.TextColumn("指标类别", width=120),
                        "指标名称": st.column_config.TextColumn("指标名称", width=120),
                        "数值": st.column_config.TextColumn("数值", width=100),
                    },
                    hide_index=True,
                )
            else:
                st.info("核心指标数据不足或计算失败。")

            # Section for Investment Advice
            st.markdown("### 💡 投资建议 (基于模型与技术信号)")
            expected_daily_return = expected_daily_return_pct
            
            signals = []
            if not stock_data.empty and len(stock_data) >= 20: # Min length for some TAs
                # MA Crossover (MA5 vs MA20)
                if 'MA5' in stock_data.columns and 'MA20' in stock_data.columns:
                    if pd.notna(stock_data['MA5'].iloc[-1]) and pd.notna(stock_data['MA20'].iloc[-1]) and \
                       pd.notna(stock_data['MA5'].iloc[-2]) and pd.notna(stock_data['MA20'].iloc[-2]):
                        if stock_data['MA5'].iloc[-2] < stock_data['MA20'].iloc[-2] and stock_data['MA5'].iloc[-1] > stock_data['MA20'].iloc[-1]:
                            signals.append("短期均线(MA5)上穿中期均线(MA20)，形成金叉 (看涨信号)")
                        elif stock_data['MA5'].iloc[-2] > stock_data['MA20'].iloc[-2] and stock_data['MA5'].iloc[-1] < stock_data['MA20'].iloc[-1]:
                            signals.append("短期均线(MA5)下穿中期均线(MA20)，形成死叉 (看跌信号)")

                # RSI State
                if 'RSI' in stock_data.columns and pd.notna(stock_data['RSI'].iloc[-1]):
                    rsi = stock_data['RSI'].iloc[-1]
                    if rsi < 30: signals.append(f"RSI ({rsi:.2f}) 进入超卖区域 (<30)，可能存在反弹机会")
                    elif rsi > 70: signals.append(f"RSI ({rsi:.2f}) 进入超买区域 (>70)，可能存在回调风险")

                # MACD Crossover
                if 'MACD' in stock_data.columns and 'Signal_Line' in stock_data.columns and \
                   pd.notna(stock_data['MACD'].iloc[-1]) and pd.notna(stock_data['Signal_Line'].iloc[-1]) and \
                   pd.notna(stock_data['MACD'].iloc[-2]) and pd.notna(stock_data['Signal_Line'].iloc[-2]):
                    if stock_data['MACD'].iloc[-2] < stock_data['Signal_Line'].iloc[-2] and stock_data['MACD'].iloc[-1] > stock_data['Signal_Line'].iloc[-1]:
                        signals.append("MACD线上穿信号线，形成金叉 (看涨信号)")
                    elif stock_data['MACD'].iloc[-2] > stock_data['Signal_Line'].iloc[-2] and stock_data['MACD'].iloc[-1] < stock_data['Signal_Line'].iloc[-1]:
                        signals.append("MACD线下穿信号线，形成死叉 (看跌信号)")
                
                # Bollinger Bands
                if 'BB_Upper' in stock_data.columns and 'BB_Lower' in stock_data.columns and 'Close' in stock_data.columns and \
                   pd.notna(stock_data['Close'].iloc[-1]) and pd.notna(stock_data['BB_Upper'].iloc[-1]) and pd.notna(stock_data['BB_Lower'].iloc[-1]):
                    if stock_data['Close'].iloc[-1] > stock_data['BB_Upper'].iloc[-1]:
                        signals.append("价格突破布林带上轨，可能超买或趋势强劲")
                    elif stock_data['Close'].iloc[-1] < stock_data['BB_Lower'].iloc[-1]:
                        signals.append("价格跌破布林带下轨，可能超卖或趋势疲弱")

                # Candlestick Patterns
                ohlc_cols = ['Open', 'High', 'Low', 'Close']
                if all(col in stock_data.columns for col in ohlc_cols) and stock_data[ohlc_cols].iloc[-len(stock_data):].notna().all().all(): # Check all needed rows for talib
                    op, hi, lo, cl = stock_data['Open'], stock_data['High'], stock_data['Low'], stock_data['Close']
                    if len(op) > 0: # Ensure there is data for TA-Lib functions
                        # Consistently use .values[-1] for TA-Lib pattern results
                        doji_pattern_output = talib.CDLDOJI(op, hi, lo, cl)
                        if doji_pattern_output.size > 0 and doji_pattern_output.values[-1] != 0: 
                            signals.append("最近K线出现十字星形态 (市场犹豫)")
                        
                        hammer_pattern_output = talib.CDLHAMMER(op, hi, lo, cl)
                        if hammer_pattern_output.size > 0 and hammer_pattern_output.values[-1] != 0:
                            signals.append("最近K线出现锤头线形态 (潜在看涨反转)")

                        engulfing_pattern_output = talib.CDLENGULFING(op, hi, lo, cl)
                        if engulfing_pattern_output.size > 0:
                            eng_signal = engulfing_pattern_output.values[-1]
                            if eng_signal == 100: signals.append("最近K线出现看涨吞没形态 (看涨信号)")
                            elif eng_signal == -100: signals.append("最近K线出现看跌吞没形态 (看跌信号)")
            
            advice_messages = []
            advice_level = "中性展望"
            advice_stars = "⭐"

            if isinstance(expected_daily_return, (int, float)):
                if expected_daily_return > 0.5: advice_level, advice_stars = "乐观展望", "⭐⭐⭐"
                elif expected_daily_return > 0.2: advice_level, advice_stars = "中性偏乐观展望", "⭐⭐"
                elif expected_daily_return < 0: advice_level, advice_stars = "谨慎展望", "❌"
                advice_messages.append(f"- 模型预测预期日收益率: {expected_daily_return:.2f}%.")
            else:
                advice_messages.append("- 预期日收益率数据缺失或无效.")

            if signals:
                advice_messages.append("- 技术面信号：")
                for signal in signals: advice_messages.append(f"  - {signal}")
            else:
                advice_messages.append("- 技术面暂无明显短期信号.")
            
            bullish_signal_count = sum(1 for s in signals if "看涨" in s or "金叉" in s or "超卖" in s or "反弹" in s) # "超卖" implies bullish potential
            bearish_signal_count = sum(1 for s in signals if "看跌" in s or "死叉" in s or "超买" in s or "回调" in s) # "超买" implies bearish potential

            final_suggestion_text = "建议结合更多信息综合判断，目前宜多观察。" # Default
            if isinstance(expected_daily_return, (int, float)):
                if expected_daily_return > 0.2 and bullish_signal_count > bearish_signal_count:
                    final_suggestion_text = "模型预测与技术信号偏积极，可考虑关注。"
                elif expected_daily_return < -0.2 and bearish_signal_count > bullish_signal_count:
                    final_suggestion_text = "模型预测与技术信号偏谨慎，注意风险。"
                elif bullish_signal_count > bearish_signal_count + 1 : # Significantly more bullish signals
                    final_suggestion_text = "技术信号显示较多积极迹象，建议结合基本面进一步判断。"
                elif bearish_signal_count > bullish_signal_count + 1: # Significantly more bearish signals
                    final_suggestion_text = "技术信号显示较多谨慎迹象，注意控制风险。"
            elif bullish_signal_count > bearish_signal_count + 1 :
                 final_suggestion_text = "技术信号显示较多积极迹象，但缺乏量化预测支持，谨慎判断。"
            elif bearish_signal_count > bullish_signal_count + 1:
                 final_suggestion_text = "技术信号显示较多谨慎迹象，注意控制风险。"


            if advice_level == "乐观展望": st.success(f"📈 {advice_level} (基于模型) {advice_stars}")
            elif advice_level == "中性偏乐观展望": st.info(f"📊 {advice_level} (基于模型) {advice_stars}")
            elif advice_level == "中性展望": st.warning(f"📉 {advice_level} (基于模型) {advice_stars}")
            else: st.error(f"⚠️ {advice_level} (基于模型) {advice_stars}")

            for msg in advice_messages: st.markdown(msg)
            st.markdown(f"- **综合建议**：{final_suggestion_text}")

            # Risk Warning Section
            st.markdown("### ⚠️ 风险提示")
            st.markdown("""
            - 以上分析仅供参考，不构成投资建议。
            - 股市有风险，投资需谨慎。
            - 过往表现不代表未来收益。
            - 建议投资者根据自身风险承受能力做出投资决策。
            """)
        except Exception as e:
            tb_str = traceback.format_exc()
            st.error(f"生成分析报告时出错: {str(e)}\n\n详细堆栈信息:\n{tb_str}")
