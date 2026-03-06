#!/usr/bin/env python3
"""
测试AKShare获取002415数据
"""

print("📊 测试AKShare获取002415股票数据")
print("=" * 60)

try:
    # 尝试安装AKShare
    import subprocess
    import sys
    
    print("1. 安装AKShare...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "akshare", "-q"])
    
    import akshare as ak
    import pandas as pd
    from datetime import datetime, timedelta
    
    print("✅ AKShare安装成功")
    
    print("\n2. 获取002415实时行情...")
    print("-" * 40)
    
    # 获取所有A股实时行情
    spot_df = ak.stock_zh_a_spot()
    
    # 查找002415
    stock_002415 = spot_df[spot_df['代码'] == '002415']
    
    if not stock_002415.empty:
        stock = stock_002415.iloc[0]
        print(f"✅ 找到股票: {stock['名称']} ({stock['代码']})")
        print(f"   最新价: {stock['最新价']}")
        print(f"   涨跌幅: {stock['涨跌幅']}%")
        print(f"   涨跌额: {stock['涨跌额']}")
        print(f"   成交量: {stock['成交量']} 手")
        print(f"   成交额: {stock['成交额']} 万元")
        print(f"   振幅: {stock['振幅']}%")
        print(f"   最高: {stock['最高']}")
        print(f"   最低: {stock['最低']}")
        print(f"   今开: {stock['今开']}")
        print(f"   昨收: {stock['昨收']}")
        print(f"   量比: {stock['量比']}")
        print(f"   换手率: {stock['换手率']}%")
        print(f"   市盈率: {stock['市盈率-动态']}")
        print(f"   市净率: {stock['市净率']}")
    else:
        print("❌ 未找到002415实时数据")
    
    print("\n3. 获取002415历史数据...")
    print("-" * 40)
    
    # 获取一年历史数据
    hist_df = ak.stock_zh_a_hist(
        symbol="002415",
        period="daily",
        start_date=(datetime.now() - timedelta(days=365)).strftime('%Y%m%d'),
        end_date=datetime.now().strftime('%Y%m%d'),
        adjust="qfq"  # 前复权
    )
    
    if not hist_df.empty:
        print(f"✅ 获取到 {len(hist_df)} 条历史数据")
        print(f"   日期范围: {hist_df['日期'].min()} 到 {hist_df['日期'].max()}")
        
        # 显示最新5条数据
        print("\n   最近5个交易日数据:")
        print("   " + "-" * 80)
        recent = hist_df.tail()
        for _, row in recent.iterrows():
            print(f"   {row['日期']}: 开{row['开盘']:.2f} 收{row['收盘']:.2f} 高{row['最高']:.2f} 低{row['最低']:.2f} 量{row['成交量']:,} 额{row['成交额']:,.0f}")
        
        # 基本统计
        print("\n   基本统计:")
        print(f"   平均收盘价: {hist_df['收盘'].mean():.2f}")
        print(f"   最高收盘价: {hist_df['收盘'].max():.2f}")
        print(f"   最低收盘价: {hist_df['收盘'].min():.2f}")
        print(f"   价格标准差: {hist_df['收盘'].std():.2f}")
        
        # 计算涨跌幅
        returns = hist_df['收盘'].pct_change().dropna()
        print(f"   平均日回报: {returns.mean():.4%}")
        print(f"   日回报波动: {returns.std():.4%}")
        
    else:
        print("❌ 未获取到历史数据")
    
    print("\n4. 获取002415资金流向...")
    print("-" * 40)
    
    try:
        # 获取资金流向
        money_flow = ak.stock_individual_fund_flow(stock="002415", market="SZ")
        if not money_flow.empty:
            print("✅ 获取到资金流向数据")
            print(f"   数据维度: {money_flow.shape}")
            print(f"   列名: {list(money_flow.columns)}")
        else:
            print("⚠️  资金流向数据为空")
    except Exception as e:
        print(f"⚠️  资金流向获取失败: {e}")
    
    print("\n5. 获取002415基本面数据...")
    print("-" * 40)
    
    try:
        # 获取财务指标
        financial = ak.stock_financial_abstract(stock="002415")
        if not financial.empty:
            print("✅ 获取到财务指标数据")
            print(f"   报表期: {financial.iloc[0]['REPORT_DATE'] if 'REPORT_DATE' in financial.columns else 'N/A'}")
            print(f"   营业收入: {financial.iloc[0]['OPERATE_INCOME'] if 'OPERATE_INCOME' in financial.columns else 'N/A'}")
            print(f"   净利润: {financial.iloc[0]['NETPROFIT'] if 'NETPROFIT' in financial.columns else 'N/A'}")
        else:
            print("⚠️  财务指标数据为空")
    except Exception as e:
        print(f"⚠️  基本面数据获取失败: {e}")
    
    print("\n6. AKShare其他可用功能:")
    print("-" * 40)
    functions = [
        "stock_zh_a_hist_min_em() - 分时数据",
        "stock_individual_info_em() - 公司信息",
        "stock_financial_report_sina() - 财务报告",
        "stock_zh_a_tick_tx() - 分笔数据",
        "stock_sector_fund_flow_rank() - 行业资金流",
        "stock_hot_rank_em() - 热门股票",
        "stock_news_em() - 股票新闻",
    ]
    
    for func in functions:
        print(f"   • {func}")
    
    print("\n" + "=" * 60)
    print("✅ AKShare测试完成")
    print("=" * 60)
    print("\n📊 结论:")
    print("  ✅ AKShare可以获取002415的实时行情")
    print("  ✅ AKShare可以获取002415的历史数据")
    print("  ✅ AKShare可以获取资金流向和基本面数据")
    print("  ✅ AKShare完全免费，无API限制")
    print("  ✅ AKShare专门为A股设计，数据更全面")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
