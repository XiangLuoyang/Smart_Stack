#!/bin/bash
# Smart Stack v1.1.0 完整发布流程

echo "🎯 Smart Stack v1.1.0 完整发布流程"
echo "="================================

echo ""
echo "📊 当前状态:"
echo "  ✅ 代码已推送到GitHub"
echo "  ✅ 版本标签 v1.1.0 已创建"
echo "  ⏳ 等待创建GitHub Release"
echo ""

echo "🚀 选择发布方式:"
echo ""
echo "1. 使用GitHub CLI (推荐)"
echo "2. 使用GitHub Token API"
echo "3. 手动网页创建"
echo "4. 查看详细指南"
echo ""

read -p "请选择 (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🔧 使用GitHub CLI创建Release..."
        echo ""
        
        # 检查是否安装gh
        if ! command -v gh &> /dev/null; then
            echo "❌ GitHub CLI 未安装"
            echo ""
            echo "安装方法:"
            echo "  macOS: brew install gh"
            echo "  Linux: sudo apt install gh"
            echo "  Windows: winget install GitHub.cli"
            echo ""
            exit 1
        fi
        
        # 检查登录状态
        if ! gh auth status &> /dev/null; then
            echo "🔐 需要登录GitHub"
            echo ""
            echo "请选择登录方式:"
            echo "  1. 浏览器登录 (推荐)"
            echo "  2. Token登录"
            echo ""
            read -p "选择登录方式 (1-2): " login_choice
            
            if [ "$login_choice" = "1" ]; then
                gh auth login
            elif [ "$login_choice" = "2" ]; then
                read -p "请输入GitHub Token: " token
                echo "$token" | gh auth login --with-token
            else
                echo "❌ 无效选择"
                exit 1
            fi
        fi
        
        echo ""
        echo "📦 创建Release v1.1.0..."
        echo ""
        
        gh release create v1.1.0 \
            --title "Smart Stack v1.1.0 - YFinance优化版" \
            --notes-file RELEASE_NOTES_v1.1.0.md \
            --target main \
            --latest
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "🎉 Release创建成功!"
            echo ""
            echo "访问链接:"
            echo "  https://github.com/XiangLuoyang/Smart_Stack/releases/tag/v1.1.0"
        else
            echo ""
            echo "❌ Release创建失败"
        fi
        ;;
    
    2)
        echo ""
        echo "🔑 使用GitHub Token API创建Release..."
        echo ""
        echo "需要GitHub Token (需要repo权限)"
        echo "获取Token: https://github.com/settings/tokens"
        echo ""
        read -p "请输入GitHub Token: " token
        
        if [ -z "$token" ]; then
            echo "❌ Token不能为空"
            exit 1
        fi
        
        export GITHUB_TOKEN="$token"
        ./CREATE_RELEASE_WITH_TOKEN.sh
        ;;
    
    3)
        echo ""
        echo "🌐 手动网页创建Release..."
        echo ""
        echo "请按以下步骤操作:"
        echo ""
        echo "1. 打开浏览器访问:"
        echo "   https://github.com/XiangLuoyang/Smart_Stack/releases"
        echo ""
        echo "2. 点击 'Draft a new release'"
        echo ""
        echo "3. 选择标签: v1.1.0"
        echo ""
        echo "4. 填写信息:"
        echo "   - 标题: Smart Stack v1.1.0 - YFinance优化版"
        echo "   - 描述: 复制以下内容"
        echo ""
        echo "5. 点击 'Publish release'"
        echo ""
        echo "📝 发布说明内容已复制到剪贴板（如果支持）"
        echo ""
        
        # 尝试复制到剪贴板
        if command -v pbcopy &> /dev/null; then
            cat RELEASE_NOTES_v1.1.0.md | pbcopy
            echo "✅ 内容已复制到macOS剪贴板"
        elif command -v xclip &> /dev/null; then
            cat RELEASE_NOTES_v1.1.0.md | xclip -selection clipboard
            echo "✅ 内容已复制到Linux剪贴板"
        elif command -v clip &> /dev/null; then
            cat RELEASE_NOTES_v1.1.0.md | clip
            echo "✅ 内容已复制到Windows剪贴板"
        else
            echo "⚠️  无法自动复制，请手动复制文件内容"
            echo "文件: RELEASE_NOTES_v1.1.0.md"
        fi
        ;;
    
    4)
        echo ""
        echo "📚 详细发布指南"
        echo ""
        cat RELEASE_SUCCESS_REPORT.md | head -50
        echo ""
        echo "... (完整内容查看 RELEASE_SUCCESS_REPORT.md)"
        ;;
    
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "📋 发布验证:"
echo ""
echo "1. 检查Release页面:"
echo "   https://github.com/XiangLuoyang/Smart_Stack/releases"
echo ""
echo "2. 验证功能:"
echo "   - 新用户安装测试"
echo "   - 核心功能测试"
echo ""
echo "3. 更新文档:"
echo "   - 确保README指向新版本"
echo "   - 更新项目描述"
echo ""

echo "🎉 Smart Stack v1.1.0 发布流程指南完成!"
echo ""
echo "项目优化成果:"
echo "  🚀 稳定性: YFinance免费无限制"
echo "  🎯 易用性: 3步安装，零配置"
echo "  🌍 功能: 支持全球市场"
echo "  💪 智能: 代码自动识别"
