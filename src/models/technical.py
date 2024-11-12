import pandas as pd
import numpy as np

class TechnicalIndicators:
    """技术指标计算类"""
    
    @staticmethod
    def calculate_ma(data: pd.DataFrame, period: int) -> pd.Series:
        """计算移动平均线"""
        return data['Close'].rolling(window=period).mean()
    
    @staticmethod
    def calculate_rsi(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        diff = data['Close'].diff()
        gain = (diff.where(diff > 0, 0)).rolling(window=period).mean()
        loss = (-diff.where(diff < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def calculate_macd(data: pd.DataFrame) -> tuple:
        """计算MACD指标"""
        exp1 = data['Close'].ewm(span=12, adjust=False).mean()
        exp2 = data['Close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal
        return macd, signal, hist

    @staticmethod
    def add_all_indicators(data: pd.DataFrame) -> pd.DataFrame:
        """添加所有技术指标"""
        try:
            # 添加移动平均线
            for period in [5, 20, 60]:
                data[f'MA{period}'] = TechnicalIndicators.calculate_ma(data, period)
            
            # 添加RSI
            data['RSI'] = TechnicalIndicators.calculate_rsi(data)
            
            # 添加MACD
            data['MACD'], data['Signal'], data['MACD_hist'] = TechnicalIndicators.calculate_macd(data)
            
            # 确保所有列都存在
            required_columns = [
                'Date', 'Open', 'High', 'Low', 'Close', 'Volume',
                'MA5', 'MA20', 'MA60', 'RSI', 'MACD', 'Signal', 'MACD_hist'
            ]
            
            for col in required_columns:
                if col not in data.columns:
                    print(f"警告：缺少列 {col}")
            
            return data
        except Exception as e:
            print(f"添加技术指标时出错: {str(e)}")
            return data

    @staticmethod
    def generate_trading_suggestion(data: pd.DataFrame) -> dict:
        """生成交易建议"""
        try:
            signals = []
            bullish_count = 0
            bearish_count = 0
            
            # 检查均线金叉/死叉
            if data['MA5'].iloc[-1] > data['MA20'].iloc[-1] and \
               data['MA5'].iloc[-2] <= data['MA20'].iloc[-2]:
                signals.append("MA5与MA20形成金叉，可能上涨")
                bullish_count += 1
            elif data['MA5'].iloc[-1] < data['MA20'].iloc[-1] and \
                 data['MA5'].iloc[-2] >= data['MA20'].iloc[-2]:
                signals.append("MA5与MA20形成死叉，可能下跌")
                bearish_count += 1
            
            # 检查RSI
            current_rsi = data['RSI'].iloc[-1]
            if current_rsi < 30:
                signals.append("RSI低于30，超卖状态，可能反弹")
                bullish_count += 1
            elif current_rsi > 70:
                signals.append("RSI高于70，超买状态，可能回调")
                bearish_count += 1
            
            # 检查MACD
            if data['MACD_hist'].iloc[-1] > 0 and data['MACD_hist'].iloc[-2] <= 0:
                signals.append("MACD金叉，可能上涨")
                bullish_count += 1
            elif data['MACD_hist'].iloc[-1] < 0 and data['MACD_hist'].iloc[-2] >= 0:
                signals.append("MACD死叉，可能下跌")
                bearish_count += 1
            
            # 生成建议
            if bullish_count > bearish_count:
                action = "买入"
                confidence = "高" if bullish_count >= 2 else "中"
            elif bearish_count > bullish_count:
                action = "卖出"
                confidence = "高" if bearish_count >= 2 else "中"
            else:
                action = "观望"
                confidence = "低"
            
            if not signals:
                signals.append("暂无明显信号")
            
            return {
                "建议操作": action,
                "信号强度": confidence,
                "具体信号": signals
            }
            
        except Exception as e:
            print(f"生成交易建议时出错: {str(e)}")
            return {
                "建议操作": "观望",
                "信号强度": "低",
                "具体信号": ["计算出错，建议观望"]
            }