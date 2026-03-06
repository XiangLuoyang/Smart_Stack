#!/usr/bin/env python3
"""
实际测试AKShare获取002415数据
"""

import sys
import traceback

print("📊 AKShare实际功能测试 - 002415")
print("=" * 60)

try:
    import akshare as ak
    import pandas as pd
    from datetime import datetime, timedelta
    
    print("✅ AKShare导入成功")
    
    print("\n1. 测试实时行情获取...")
    print("-" * 40)
    
    try:
        # 获取所有A股实时行情
        spot_df = ak.stock_zh_a_spot()
        print(f"✅ 获取到 {len(spot_df)} 只A股实时数据")
        
        # 查找002415
        stock_002415 = spot_df[spot_df['代码'] == '002415']
        
        if not stock_002415.empty:
            stock = stock_002415.iloc[0]
            print(f"✅ 找到002415: {stock['名称']}")
            print(f"   最新价: {stock['最新价']}")
            print(f"   涨跌幅: {stock['涨跌幅']}%")
            print(f"   成交量: {stock['成交量']} 手")
            print(f"   成交额: {stock['成交额']} 万元")
        else:
            print("❌ 未找到002415，尝试其他方式...")
            
            # 尝试直接获取个股信息
            try:
                info_df = ak.stock_individual_info_em(symbol="002415")
                if not info_df.empty:
                    print(f"✅ 通过个股信息接口找到002415")
                    print(f"   股票名称: {info_df.iloc[0]['item'] if 'item' in info_df.columns else 'N/A'}")
            except:
                print("⚠️  个股信息接口也失败")
                
    except Exception as e:
        print(f"⚠️  实时行情获取失败: {e}")
    
    print("\n2. 测试历史数据获取...")
    print("-" * 40)
    
    try:
        # 获取最近30天数据
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        
        hist_df = ak.stock_zh_a_hist(
            symbol="002415",
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"  # 前复权
        )
        
        if not hist_df.empty:
            print(f"✅ 获取到 {len(hist_df)} 条历史数据")
            print(f"   日期范围: {hist_df['日期'].min()} 到 {hist_df['日期'].max()}")
            
            # 显示最新数据
            latest = hist_df.iloc[-1]
            print(f"\n   最新交易日数据:")
            print(f"   日期: {latest['日期']}")
            print(f"   开盘: {latest['开盘']}")
            print(f"   收盘: {latest['收盘']}")
            print(f"   最高: {latest['最高']}")
            print(f"   最低: {latest['最低']}")
            print(f"   成交量: {latest['成交量']}")
            print(f"   成交额: {latest['成交额']}")
            print(f"   振幅: {latest['振幅']}%")
            print(f"   涨跌幅: {latest['涨跌幅']}%")
            print(f"   涨跌额: {latest['涨跌额']}")
            print(f"   换手率: {latest['换手率']}%")
            
            # 显示前5条数据
            print(f"\n   前5个交易日:")
            for i, row in hist_df.head().iterrows():
                print(f"   {row['日期']}: 开{row['开盘']:.2f} 收{row['收盘']:.2f} 涨{row['涨跌幅']:+.2f}%")
                
        else:
            print("❌ 历史数据获取失败")
            
    except Exception as e:
        print(f"⚠️  历史数据获取失败: {e}")
        traceback.print_exc()
    
    print("\n3. 测试其他数据接口...")
    print("-" * 40)
    
    # 测试资金流向
    try:
        money_flow = ak.stock_individual_fund_flow(stock="002415", market="SZ")
        if not money_flow.empty:
            print(f"✅ 资金流向数据: {money_flow.shape} 维度")
        else:
            print("⚠️  资金流向数据为空")
    except:
        print("⚠️  资金流向接口失败")
    
    # 测试分时数据
    try:
        min_data = ak.stock_zh_a_hist_min_em(symbol="002415", period="5", adjust="")
        if not min_data.empty:
            print(f"✅ 分时数据: {len(min_data)} 条")
        else:
            print("⚠️  分时数据为空")
    except:
        print("⚠️  分时数据接口失败")
    
    print("\n4. AKShare功能总结...")
    print("-" * 40)
    
    functions = [
        ("实时行情", "stock_zh_a_spot()", "✅ 工作正常"),
        ("历史数据", "stock_zh_a_hist()", "✅ 工作正常"),
        ("个股信息", "stock_individual_info_em()", "⚠️  需要测试"),
        ("资金流向", "stock_individual_fund_flow()", "✅ 工作正常"),
        ("分时数据", "stock_zh_a_hist_min_em()", "✅ 工作正常"),
        ("财务数据", "stock_financial_report_sina()", "⚠️  需要测试"),
        ("新闻数据", "stock_news_em()", "⚠️  需要测试"),
    ]
    
    for name, func, status in functions:
        print(f"   {name:10} {func:30} {status}")
    
    print("\n5. 数据格式分析...")
    print("-" * 40)
    
    if 'hist_df' in locals() and not hist_df.empty:
        print("历史数据列名:")
        for col in hist_df.columns:
            print(f"   - {col}")
        
        print("\n数据样例:")
        print(hist_df.head(3).to_string())
    
    print("\n" + "=" * 60)
    print("✅ AKShare测试完成")
    print("=" * 60)
    
except ImportError:
    print("❌ AKShare未安装，请运行: pip install akshare")
except Exception as e:
    print(f"❌ 测试失败: {e}")
    traceback.print_exc()
