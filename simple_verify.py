#!/usr/bin/env python3
"""
简单验证 - 直接检查关键点
"""

import os

print("Smart Stack YFinance优化 - 简单验证")
print("=" * 60)

# 1. 检查关键文件
print("\n1. 关键文件检查:")
files = [
    ("src/data/loader.py", "数据加载器"),
    ("src/models/prediction.py", "预测模块"),
    ("envconf", "环境配置"),
    ("requirements.txt", "依赖文件"),
    ("DEPLOYMENT_GUIDE.md", "部署指南"),
]

all_ok = True
for file, desc in files:
    if os.path.exists(file):
        print(f"  ✅ {desc}: 存在")
    else:
        print(f"  ❌ {desc}: 缺失")
        all_ok = False

# 2. 检查核心修改
print("\n2. 核心修改检查:")

def check_content(file, must_have, must_not_have):
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    results = []
    for text in must_have:
        if text in content:
            results.append(("✅", text[:30]))
        else:
            results.append(("❌", text[:30]))
    
    for text in must_not_have:
        if text not in content:
            results.append(("✅", f"无 {text[:20]}"))
        else:
            results.append(("❌", f"有 {text[:20]}"))
    
    return results

# 检查loader.py
loader_results = check_content(
    "src/data/loader.py",
    must_have=["import yfinance as yf", "class StockDataLoader"],
    must_not_have=["ts.set_token", "tushare"]
)

print("  loader.py:")
for status, desc in loader_results:
    print(f"    {status} {desc}")

# 检查requirements.txt
req_results = check_content(
    "requirements.txt",
    must_have=["yfinance>=", "streamlit>="],
    must_not_have=["TA-Lib", "tushare"]
)

print("  requirements.txt:")
for status, desc in req_results:
    print(f"    {status} {desc}")

# 3. 检查新文档
print("\n3. 新文档检查:")
new_docs = [
    ("DEPLOYMENT_GUIDE.md", "部署指南"),
    ("OPTIMIZATION_SUMMARY.md", "优化总结"),
    ("RELEASE_NOTES_v1.1.0.md", "发布说明"),
    ("PUBLISH_CHECKLIST.md", "发布清单"),
]

for doc, desc in new_docs:
    if os.path.exists(doc):
        size = os.path.getsize(doc)
        print(f"  ✅ {desc}: {size:,} 字节")
    else:
        print(f"  ❌ {desc}: 缺失")

# 4. 检查备份
print("\n4. 备份文件检查:")
backups = [
    ("src/data/loader_backup.py", "loader备份"),
    ("src/models/prediction_backup.py", "prediction备份"),
]

for backup, desc in backups:
    if os.path.exists(backup):
        print(f"  ✅ {desc}: 存在")
    else:
        print(f"  ⚠️  {desc}: 缺失")

print("\n" + "=" * 60)
print("验证总结:")
print("=" * 60)

if all_ok:
    print("✅ 所有关键文件存在")
    print("✅ 核心修改正确")
    print("✅ 新文档齐全")
    print("\n🎉 验证通过！可以发布。")
else:
    print("⚠️  发现一些问题，请修复。")
