#!/usr/bin/env python3
"""
轻量级功能测试 - 不依赖完整安装
"""

print("Smart Stack YFinance修复 - 轻量级测试")
print("=" * 60)

# 1. 检查文件完整性
print("\n1. 文件完整性检查:")
import os

essential_files = [
    ("src/data/loader.py", "核心数据加载器"),
    ("src/models/prediction.py", "预测模块"),
    ("envconf", "环境配置"),
    ("requirements.txt", "依赖列表"),
    ("DEPLOYMENT_GUIDE.md", "部署指南"),
]

all_files_ok = True
for file_path, description in essential_files:
    if os.path.exists(file_path):
        size = os.path.getsize(file_path)
        print(f"  ✅ {description}: {size:,} 字节")
    else:
        print(f"  ❌ {description}: 文件缺失")
        all_files_ok = False

# 2. 检查关键代码修改
print("\n2. 关键代码修改检查:")

def check_file_content(file_path, must_have, must_not_have):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    results = []
    for text, description in must_have:
        if text in content:
            results.append((f"✅ {description}", True))
        else:
            results.append((f"❌ {description}", False))
    
    for text, description in must_not_have:
        if text not in content:
            results.append((f"✅ {description}", True))
        else:
            results.append((f"❌ {description}", False))
    
    return results

# 检查loader.py
loader_checks = check_file_content(
    "src/data/loader.py",
    must_have=[
        ("import yfinance as yf", "YFinance导入"),
        ("def _standardize_stock_code", "代码标准化函数"),
        ("def _standardize_yfinance_data", "数据标准化函数"),
        ("def get_market_info", "市场信息函数"),
    ],
    must_not_have=[
        ("ts.set_token", "Tushare硬编码"),
        ("tushare", "Tushare导入"),
    ]
)

print("  loader.py检查:")
for result, _ in loader_checks:
    print(f"    {result}")

# 检查prediction.py
prediction_checks = check_file_content(
    "src/models/prediction.py", 
    must_have=[
        ("from src.data.loader import StockDataLoader", "统一数据加载器导入"),
        ("self.data_loader = StockDataLoader", "数据加载器初始化"),
    ],
    must_not_have=[
        ("ts.set_token", "Tushare设置"),
        ("tushare_token", "Tushare Token"),
    ]
)

print("  prediction.py检查:")
for result, _ in prediction_checks:
    print(f"    {result}")

# 3. 检查配置模板
print("\n3. 配置模板检查:")
with open("envconf", 'r', encoding='utf-8') as f:
    env_content = f.read()

if "TUSHARE_TOKEN" not in env_content and "YFinance" in env_content:
    print("  ✅ 配置模板已更新（移除Tushare，添加YFinance说明）")
else:
    print("  ❌ 配置模板未正确更新")

# 4. 检查依赖文件
print("\n4. 依赖文件检查:")
with open("requirements.txt", 'r', encoding='utf-8') as f:
    req_content = f.read()

if "yfinance>=" in req_content and "TA-Lib" not in req_content:
    print("  ✅ 依赖文件已优化（添加yfinance，移除TA-Lib）")
else:
    print("  ❌ 依赖文件未正确优化")

# 5. 检查文档更新
print("\n5. 文档更新检查:")
docs_to_check = [
    ("DEPLOYMENT_GUIDE.md", "YFinance", "部署指南"),
    ("OPTIMIZATION_SUMMARY.md", "优化总结", "总结文档"),
    ("README.md", "YFinance", "README"),
]

for doc_file, keyword, description in docs_to_check:
    if os.path.exists(doc_file):
        with open(doc_file, 'r', encoding='utf-8') as f:
            if keyword in f.read():
                print(f"  ✅ {description}: 已更新")
            else:
                print(f"  ⚠️  {description}: 可能未完全更新")
    else:
        print(f"  ❌ {description}: 文件缺失")

# 6. 语法检查
print("\n6. Python语法检查:")

def check_syntax(file_path):
    import subprocess
    result = subprocess.run(
        ["python3", "-m", "py_compile", file_path],
        capture_output=True,
        text=True
    )
    return result.returncode == 0

files_to_check = [
    "src/data/loader.py",
    "src/models/prediction.py",
]

for file_path in files_to_check:
    if check_syntax(file_path):
        print(f"  ✅ {os.path.basename(file_path)}: 语法正确")
    else:
        print(f"  ❌ {os.path.basename(file_path)}: 语法错误")

# 总结
print("\n" + "=" * 60)
print("测试总结:")
print("=" * 60)

all_checks = loader_checks + prediction_checks
passed = sum(1 for _, ok in all_checks if ok)
total = len(all_checks)

print(f"代码检查: {passed}/{total} 通过")
print(f"文件完整性: {'✅ 全部存在' if all_files_ok else '❌ 有文件缺失'}")
print(f"配置更新: {'✅ 已完成' if 'TUSHARE_TOKEN' not in env_content else '❌ 未完成'}")
print(f"依赖优化: {'✅ 已完成' if 'yfinance>=' in req_content else '❌ 未完成'}")

if passed == total and all_files_ok:
    print("\n🎉 所有基础检查通过！可以进入功能测试阶段。")
else:
    print("\n⚠️  发现一些问题，请先修复。")

print("\n下一步:")
print("1. 完整环境安装测试")
print("2. 功能集成测试")
print("3. 发布到GitHub")
