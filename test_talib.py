import numpy as np
import talib

# 创建一些示例数据
close = np.random.random(100)

# 测试一些TA-Lib函数
sma = talib.SMA(close, timeperiod=10)
rsi = talib.RSI(close, timeperiod=14)
upper, middle, lower = talib.BBANDS(close, timeperiod=20)

print("TA-Lib测试成功!")
print(f"SMA(10)最后一个值: {sma[-1]}")
print(f"RSI(14)最后一个值: {rsi[-1]}")
print(f"BBANDS(20)最后一个值: {upper[-1]}, {middle[-1]}, {lower[-1]}")
