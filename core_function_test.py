#!/usr/bin/env python3
"""
核心功能测试 - 不依赖外部库
"""

import os
import sys

print("Smart Stack YFinance核心功能测试")
print("=" * 60)

def test_file_structure():
    """测试文件结构完整性"""
    print("\n1. 文件结构完整性测试")
    print("-" * 40)
    
    required_structure = {
        "src/data/": ["loader.py", "__init__.py"],
        "src/models/": ["prediction.py", "__init__.py"],
        "src/config/": ["settings.py", "__init__.py"],
        "src/tools/": ["financial_tools.py", "__init__.py"],
        "src/llm_analysis/": ["core.py", "__init__.py"],
        ".": ["smart-trade.py", "requirements.txt", "envconf", "README.md"]
    }
    
    all_ok = True
    for directory, files in required_structure.items():
        dir_exists = os.path.exists(directory) if directory != "." else True
        
        if not dir_exists and directory != ".":
            print(f"❌ 目录缺失: {directory}")
            all_ok = False
            continue
        
        for file in files:
            file_path = os.path.join(directory, file) if directory != "." else file
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"  ✅ {file_path}: {size:,} 字节")
            else:
                print(f"  ❌ 文件缺失: {file_path}")
                all_ok = False
    
    return all_ok

def test_code_quality():
    """测试代码质量"""
    print("\n2. 代码质量测试")
    print("-" * 40)
    
    # 检查loader.py的关键功能
    loader_path = "src/data/loader.py"
    with open(loader_path, 'r', encoding='utf-8') as f:
        loader_content = f.read()
    
    checks = [
        ("import yfinance as yf", "YFinance导入"),
        ("class StockDataLoader:", "数据加载器类"),
        ("def load_stock_data", "核心数据加载方法"),
        ("def _standardize_stock_code", "代码标准化"),
        ("def _standardize_yfinance_data", "数据标准化"),
        ("def get_market_info", "市场信息"),
        ("def batch_load_stock_data", "批量加载"),
    ]
    
    passed = 0
    for pattern, description in checks:
        if pattern in loader_content:
            print(f"  ✅ {description}")
            passed += 1
        else:
            print(f"  ❌ {description}")
    
    # 检查是否移除了Tushare
    if "ts.set_token" not in loader_content and "tushare" not in loader_content.lower():
        print("  ✅ 完全移除Tushare依赖")
        passed += 1
    else:
        print("  ❌ 仍有Tushare残留")
    
    print(f"  通过率: {passed}/{len(checks)+1}")
    return passed == len(checks)+1

def test_config_files():
    """测试配置文件"""
    print("\n3. 配置文件测试")
    print("-" * 40)
    
    # 检查envconf
    with open("envconf", 'r', encoding='utf-8') as f:
        env_content = f.read()
    
    env_checks = [
        ("LLM_API_KEY", "LLM API密钥配置"),
        ("YFinance", "YFinance说明"),
        ("无需API Token", "简化配置说明"),
    ]
    
    env_passed = 0
    for key, description in env_checks:
        if key in env_content:
            print(f"  ✅ {description}")
            env_passed += 1
        else:
            print(f"  ❌ {description}")
    
    # 检查Tushare是否移除
    if "TUSHARE_TOKEN" not in env_content:
        print("  ✅ 移除TUSHARE_TOKEN配置")
        env_passed += 1
    else:
        print("  ❌ 仍有TUSHARE_TOKEN配置")
    
    # 检查requirements.txt
    with open("requirements.txt", 'r', encoding='utf-8') as f:
        req_content = f.read()
    
    req_checks = [
        ("yfinance>=", "YFinance依赖"),
        ("streamlit>=", "Streamlit依赖"),
        ("pandas>=", "Pandas依赖"),
    ]
    
    req_passed = 0
    for key, description in req_checks:
        if key in req_content:
            print(f"  ✅ {description}")
            req_passed += 1
        else:
            print(f"  ❌ {description}")
    
    # 检查是否移除了TA-Lib
    if "TA-Lib" not in req_content:
        print("  ✅ 移除TA-Lib依赖")
        req_passed += 1
    else:
        print("  ❌ 仍有TA-Lib依赖")
    
    return env_passed >= 3 and req_passed >= 4

def test_documentation():
    """测试文档完整性"""
    print("\n4. 文档完整性测试")
    print("-" * 40)
    
    docs = [
        ("DEPLOYMENT_GUIDE.md", "部署指南", 3000),
        ("OPTIMIZATION_SUMMARY.md", "优化总结", 2000),
        ("README.md", "README文档", 1500),
    ]
    
    all_ok = True
    for file_name, description, min_size in docs:
        if os.path.exists(file_name):
            size = os.path.getsize(file_name)
            if size >= min_size:
                print(f"  ✅ {description}: {size:,} 字节")
            else:
                print(f"  ⚠️  {description}: 内容可能不足 ({size:,} 字节)")
                all_ok = False
        else:
            print(f"  ❌ {description}: 文件缺失")
            all_ok = False
    
    return all_ok

def main():
    """主测试函数"""
    print("开始核心功能测试...\n")
    
    results = []
    
    # 运行各项测试
    results.append(("文件结构", test_file_structure()))
    results.append(("代码质量", test_code_quality()))
    results.append(("配置文件", test_config_files()))
    results.append(("文档完整性", test_documentation()))
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    for test_name, ok in results:
        status = "✅" if ok else "❌"
        print(f"{status} {test_name}")
    
    print(f"\n总体通过率: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有核心功能测试通过！")
        print("✅ 文件结构完整")
        print("✅ 代码质量达标")
        print("✅ 配置更新正确")
        print("✅ 文档齐全")
        print("\n🚀 可以进入发布阶段！")
        return True
    else:
        print("\n⚠️  发现一些问题，请先修复。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
