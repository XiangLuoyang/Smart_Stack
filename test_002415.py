#!/usr/bin/env python3
"""
测试Smart Stack v1.1.0的002415股票分析功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("📊 Smart Stack v1.1.0 - 002415股票分析测试")
print("=" * 60)

# 模拟Streamlit环境
class MockStreamlit:
    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARNING] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")
    def success(self, msg): print(f"[SUCCESS] {msg}")

# 导入并测试数据加载器
print("\n1. 测试数据加载器...")
print("-" * 40)

try:
    # 临时替换streamlit
    import src.data.loader as loader_module
    loader_module.st = MockStreamlit()
    
    from src.config.settings import DataConfig
    from src.data.loader import StockDataLoader
    
    # 初始化数据加载器
    data_config = DataConfig()
    loader = StockDataLoader(data_config)
    
    print("✅ 数据加载器初始化成功")
    
    # 测试002415股票
    stock_code = "002415"
    print(f"\n2. 分析股票: {stock_code}")
    print("-" * 40)
    
    # 获取数据
    df, standardized_code = loader.load_stock_data(stock_code)
    
    if not df.empty:
        print(f"✅ 数据获取成功")
        print(f"   标准化代码: {standardized_code}")
        print(f"   数据条数: {len(df)} 条")
        print(f"   日期范围: {df['Date'].min()} 到 {df['Date'].max()}")
        print(f"   最新数据:")
        latest = df.iloc[-1]
        print(f"     - 日期: {latest['Date']}")
        print(f"     - 收盘价: {latest.get('Close', 'N/A')}")
        print(f"     - 开盘价: {latest.get('Open', 'N/A')}")
        print(f"     - 最高价: {latest.get('High', 'N/A')}")
        print(f"     - 最低价: {latest.get('Low', 'N/A')}")
        print(f"     - 成交量: {latest.get('Volume', 'N/A')}")
    else:
        print("❌ 数据获取失败，股票代码可能无效")
    
    # 测试市场信息
    print(f"\n3. 市场信息检测")
    print("-" * 40)
    
    market_info = loader.get_market_info(stock_code)
    if 'error' not in market_info:
        print(f"✅ 市场信息获取成功")
        print(f"   股票名称: {market_info.get('name', 'N/A')}")
        print(f"   所属市场: {market_info.get('market', 'N/A')}")
        print(f"   货币: {market_info.get('currency', 'N/A')}")
        print(f"   时区: {market_info.get('timezone', 'N/A')}")
    else:
        print(f"⚠️  市场信息获取失败: {market_info.get('error', '未知错误')}")
    
    # 测试预测模块
    print(f"\n4. 预测分析测试")
    print("-" * 40)
    
    try:
        import src.models.prediction as prediction_module
        prediction_module.st = MockStreamlit()
        
        from src.models.prediction import ReturnPredictor
        from datetime import datetime
        
        predictor = ReturnPredictor()
        print("✅ 预测器初始化成功")
        
        # 计算预期回报率
        start_date = datetime(2025, 1, 1)
        result = predictor.calculate_expected_return(
            ticker=standardized_code,
            start_date=start_date,
            window=30,
            confidence=0.95
        )
        
        if "error" not in result:
            print(f"✅ 预期回报率计算成功")
            print(f"   预期日回报率: {result.get('expected_daily_return', 0):.4%}")
            print(f"   日波动率: {result.get('daily_std', 0):.4%}")
            print(f"   年化回报率: {result.get('annualized_return', 0):.2%}")
            print(f"   数据点数: {result.get('data_points', 0)}")
            
            ci = result.get('confidence_interval', {})
            if ci:
                print(f"   95%置信区间: [{ci.get('lower', 0):.4%}, {ci.get('upper', 0):.4%}]")
        else:
            print(f"⚠️  回报率计算失败: {result.get('error', '未知错误')}")
            
    except Exception as e:
        print(f"⚠️  预测模块测试失败: {e}")
    
    # 显示数据样本
    print(f"\n5. 数据样本 (前5行)")
    print("-" * 40)
    if not df.empty:
        sample = df.head()
        for i, row in sample.iterrows():
            print(f"   {row['Date']}: 开{row.get('Open', 'N/A')} 收{row.get('Close', 'N/A')} 高{row.get('High', 'N/A')} 低{row.get('Low', 'N/A')} 量{row.get('Volume', 'N/A')}")
    
    print(f"\n6. 数据统计")
    print("-" * 40)
    if not df.empty and 'Close' in df.columns:
        close_prices = df['Close']
        print(f"   平均收盘价: {close_prices.mean():.2f}")
        print(f"   最高收盘价: {close_prices.max():.2f}")
        print(f"   最低收盘价: {close_prices.min():.2f}")
        print(f"   价格波动: {close_prices.std():.2f}")
        
        # 计算涨跌幅
        if len(close_prices) > 1:
            returns = close_prices.pct_change().dropna()
            print(f"   平均日回报: {returns.mean():.4%}")
            print(f"   日回报波动: {returns.std():.4%}")
    
except Exception as e:
    print(f"❌ 测试过程中出错: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ Smart Stack v1.1.0 测试完成")
print("=" * 60)
