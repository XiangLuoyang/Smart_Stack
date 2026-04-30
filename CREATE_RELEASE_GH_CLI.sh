#!/bin/bash
# 使用GitHub CLI创建Release

echo "📦 使用GitHub CLI创建Smart Stack v1.1.0 Release"
echo "="============================================

# 检查是否安装了gh CLI
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) 未安装"
    echo ""
    echo "安装方法:"
    echo "  macOS: brew install gh"
    echo "  Linux: sudo apt install gh 或参考 https://github.com/cli/cli#installation"
    echo "  Windows: winget install --id GitHub.cli"
    echo ""
    exit 1
fi

# 检查是否已登录
if ! gh auth status &> /dev/null; then
    echo "❌ 未登录GitHub，请先登录:"
    echo "  gh auth login"
    echo ""
    exit 1
fi

echo "✅ GitHub CLI 已安装并登录"
echo ""

# 创建Release
echo "🚀 创建Release v1.1.0..."
echo ""

# 读取发布说明
RELEASE_BODY=$(cat RELEASE_NOTES_v1.1.0.md)

# 使用gh创建Release
gh release create v1.1.0 \
    --title "Smart Stack v1.1.0 - YFinance优化版" \
    --notes "$RELEASE_BODY" \
    --target main \
    --latest

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Release创建成功!"
    echo ""
    echo "访问链接:"
    echo "  https://github.com/XiangLuoyang/Smart_Stack/releases/tag/v1.1.0"
    echo ""
    echo "发布内容:"
    echo "  - 版本: v1.1.0"
    echo "  - 目标分支: main"
    echo "  - 提交: e9418b2"
    echo "  - 设置为最新版本: 是"
    echo ""
else
    echo ""
    echo "❌ Release创建失败"
    echo "请手动创建: https://github.com/XiangLuoyang/Smart_Stack/releases/new"
    echo ""
fi

echo "📊 发布验证:"
echo ""
echo "1. 检查Release页面:"
echo "   gh release view v1.1.0"
echo ""
echo "2. 查看发布列表:"
echo "   gh release list"
echo ""
echo "3. 测试下载:"
echo "   gh release download v1.1.0"
echo ""
echo "✅ Smart Stack v1.1.0 发布完成!"
