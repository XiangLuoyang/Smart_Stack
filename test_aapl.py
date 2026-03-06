#!/usr/bin/env python3
"""
测试Smart Stack v1.1.0的AAPL股票分析功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("📊 Smart Stack v1.1.0 - AAPL股票分析测试")
print("=" * 60)

# 模拟Streamlit环境
class MockStreamlit:
    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARNING] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")
    def success(self, msg): print(f"[SUCCESS] {msg}")

print("\n1. 测试YFinance直接获取AAPL数据...")
print("-" * 40)

try:
    import yfinance as yf
    import pandas as pd
    from datetime import datetime
    
    # 直接使用YFinance获取AAPL数据
    ticker = yf.Ticker("AAPL")
    
    print("✅ YFinance初始化成功")
    
    # 获取基本信息
    info = ticker.info
    print(f"\n2. 股票基本信息:")
    print("-" * 40)
    print(f"   名称: {info.get('longName', info.get('shortName', 'N/A'))}")
    print(f"   代码: AAPL")
    print(f"   行业: {info.get('industry', 'N/A')}")
    print(f"   板块: {info.get('sector', 'N/A')}")
    print(f"   国家: {info.get('country', 'N/A')}")
    print(f"   货币: {info.get('currency', 'N/A')}")
    print(f"   交易所: {info.get('exchange', 'N/A')}")
    print(f"   市值: {info.get('marketCap', 'N/A'):,}")
    
    # 获取历史数据
    print(f"\n3. 历史数据获取:")
    print("-" * 40)
    
    hist = ticker.history(period="1mo")  # 最近1个月数据
    
    if not hist.empty:
        print(f"✅ 获取到 {len(hist)} 条历史数据")
        print(f"   日期范围: {hist.index.min()} 到 {hist.index.max()}")
        
        # 显示最新数据
        latest = hist.iloc[-1]
        print(f"\n4. 最新交易日数据:")
        print("-" * 40)
        print(f"   日期: {latest.name.date()}")
        print(f"   开盘价: ${latest['Open']:.2f}")
        print(f"   收盘价: ${latest['Close']:.2f}")
        print(f"   最高价: ${latest['High']:.2f}")
        print(f"   最低价: ${latest['Low']:.2f}")
        print(f"   成交量: {latest['Volume']:,}")
        
        # 计算涨跌幅
        if len(hist) > 1:
            prev_close = hist.iloc[-2]['Close']
            change = latest['Close'] - prev_close
            change_pct = (change / prev_close) * 100
            print(f"   涨跌: ${change:+.2f} ({change_pct:+.2f}%)")
        
        # 显示数据样本
        print(f"\n5. 最近5个交易日数据:")
        print("-" * 40)
        sample = hist.tail()
        for date, row in sample.iterrows():
            print(f"   {date.date()}: 开${row['Open']:.2f} 收${row['Close']:.2f} 高${row['High']:.2f} 低${row['Low']:.2f}")
        
        # 基本统计
        print(f"\n6. 基本统计信息:")
        print("-" * 40)
        print(f"   平均收盘价: ${hist['Close'].mean():.2f}")
        print(f"   最高收盘价: ${hist['Close'].max():.2f} (日期: {hist['Close'].idxmax().date()})")
        print(f"   最低收盘价: ${hist['Close'].min():.2f} (日期: {hist['Close'].idxmin().date()})")
        print(f"   价格波动: ${hist['Close'].std():.2f}")
        
        # 计算简单技术指标
        print(f"\n7. 简单技术分析:")
        print("-" * 40)
        
        # 移动平均线
        ma5 = hist['Close'].rolling(window=5).mean()
        ma10 = hist['Close'].rolling(window=10).mean()
        
        if len(ma5) > 0 and not pd.isna(ma5.iloc[-1]):
            print(f"   5日移动平均: ${ma5.iloc[-1]:.2f}")
            print(f"   10日移动平均: ${ma10.iloc[-1]:.2f}")
            
            # 判断趋势
            current_price = latest['Close']
            if current_price > ma5.iloc[-1] and current_price > ma10.iloc[-1]:
                print(f"   趋势: 📈 上涨趋势 (价格在均线之上)")
            elif current_price < ma5.iloc[-1] and current_price < ma10.iloc[-1]:
                print(f"   趋势: 📉 下跌趋势 (价格在均线之下)")
            else:
                print(f"   趋势: ↔️  震荡整理")
        
        # 成交量分析
        avg_volume = hist['Volume'].mean()
        latest_volume = latest['Volume']
        volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 0
        
        print(f"\n8. 成交量分析:")
        print("-" * 40)
        print(f"   平均成交量: {avg_volume:,.0f}")
        print(f"   最新成交量: {latest_volume:,.0f}")
        print(f"   成交量比率: {volume_ratio:.2f}x")
        
        if volume_ratio > 1.5:
            print(f"   成交量状态: 🔥 放量交易")
        elif volume_ratio < 0.5:
            print(f"   成交量状态: ❄️  缩量交易")
        else:
            print(f"   成交量状态: ⚖️  正常交易量")
    
    else:
        print("❌ 未获取到历史数据")
    
    # 测试Smart Stack的数据加载器
    print(f"\n9. 测试Smart Stack数据加载器:")
    print("-" * 40)
    
    try:
        import src.data.loader as loader_module
        loader_module.st = MockStreamlit()
        
        from src.config.settings import DataConfig
        from src.data.loader import StockDataLoader
        
        data_config = DataConfig()
        loader = StockDataLoader(data_config)
        
        print("✅ Smart Stack数据加载器初始化成功")
        
        # 测试AAPL
        df, code = loader.load_stock_data("AAPL")
        if not df.empty:
            print(f"✅ 通过Smart Stack获取AAPL数据成功")
            print(f"   获取到 {len(df)} 条数据")
            print(f"   标准化代码: {code}")
        else:
            print("⚠️  Smart Stack数据获取失败")
            
    except Exception as e:
        print(f"⚠️  Smart Stack测试失败: {e}")
    
except Exception as e:
    print(f"❌ 测试过程中出错: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ Smart Stack v1.1.0 功能测试完成")
print("=" * 60)
