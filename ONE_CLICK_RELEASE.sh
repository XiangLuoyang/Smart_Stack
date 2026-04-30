#!/bin/bash
# Smart Stack v1.1.0 一键发布脚本

echo "🎯 Smart Stack v1.1.0 一键发布"
echo "="============================

echo ""
echo "📊 发布状态检查..."
echo ""

# 检查代码是否已推送
if git ls-remote --tags origin | grep -q "v1.1.0"; then
    echo "✅ 版本标签 v1.1.0 已存在于GitHub"
else
    echo "❌ 版本标签未找到，请先推送:"
    echo "   git push origin v1.1.0"
    exit 1
fi

echo ""
echo "🚀 开始创建GitHub Release..."
echo ""

# 方法1: 尝试使用gh（如果可用）
if command -v gh &> /dev/null; then
    echo "🔧 检测到GitHub CLI，尝试使用..."
    if gh auth status &> /dev/null; then
        echo "✅ GitHub CLI 已登录"
        echo ""
        echo "📦 创建Release..."
        gh release create v1.1.0 \
            --title "Smart Stack v1.1.0 - YFinance优化版" \
            --notes-file RELEASE_NOTES_v1.1.0.md \
            --target main \
            --latest
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "🎉 GitHub CLI创建成功!"
            echo "🔗 https://github.com/XiangLuoyang/Smart_Stack/releases/tag/v1.1.0"
            exit 0
        else
            echo "❌ GitHub CLI创建失败"
        fi
    else
        echo "⚠️  GitHub CLI未登录"
    fi
fi

echo ""
echo "📋 请选择发布方式:"
echo ""
echo "A. 自动创建 (需要GitHub Token)"
echo "B. 手动创建 (打开浏览器)"
echo "C. 查看详细指南"
echo ""

read -p "请选择 (A/B/C): " choice

case $choice in
    A|a)
        echo ""
        echo "🔑 自动创建Release..."
        echo ""
        echo "需要GitHub Token (获取: https://github.com/settings/tokens)"
        echo "Token需要 'repo' 权限"
        echo ""
        read -p "请输入GitHub Token: " token
        
        if [ -z "$token" ]; then
            echo "❌ Token不能为空"
            exit 1
        fi
        
        # 使用API创建
        echo ""
        echo "📦 调用GitHub API..."
        
        # 准备JSON数据
        RELEASE_JSON=$(cat <<JSON
{
  "tag_name": "v1.1.0",
  "target_commitish": "main",
  "name": "Smart Stack v1.1.0 - YFinance优化版",
  "body": "$(sed 's/"/\\"/g' RELEASE_NOTES_v1.1.0.md | sed ':a;N;$!ba;s/\n/\\n/g')",
  "draft": false,
  "prerelease": false
}
JSON
        )
        
        # 发送请求
        response=$(curl -s -w "\n%{http_code}" \
          -X POST \
          -H "Authorization: token $token" \
          -H "Accept: application/vnd.github.v3+json" \
          -H "Content-Type: application/json" \
          -d "$RELEASE_JSON" \
          https://api.github.com/repos/XiangLuoyang/Smart_Stack/releases)
        
        http_code=$(echo "$response" | tail -1)
        
        if [ "$http_code" = "201" ]; then
            echo "🎉 Release创建成功!"
            echo "🔗 https://github.com/XiangLuoyang/Smart_Stack/releases/tag/v1.1.0"
        else
            echo "❌ 创建失败 (HTTP: $http_code)"
            echo "请手动创建"
        fi
        ;;
    
    B|b)
        echo ""
        echo "🌐 手动创建Release..."
        echo ""
        echo "请按以下步骤操作:"
        echo ""
        echo "1. 打开浏览器:"
        echo "   https://github.com/XiangLuoyang/Smart_Stack/releases/new"
        echo ""
        echo "2. 选择标签: v1.1.0"
        echo ""
        echo "3. 填写信息:"
        echo "   - 标题: Smart Stack v1.1.0 - YFinance优化版"
        echo "   - 描述: 复制 RELEASE_NOTES_v1.1.0.md 内容"
        echo ""
        echo "4. 点击 'Publish release'"
        echo ""
        echo "📝 发布说明已准备好"
        echo ""
        
        # 显示前几行内容
        echo "发布说明预览:"
        echo "----------------------------------------------------------------"
        head -20 RELEASE_NOTES_v1.1.0.md
        echo "..."
        echo "----------------------------------------------------------------"
        echo ""
        echo "完整内容在: RELEASE_NOTES_v1.1.0.md"
        ;;
    
    C|c)
        echo ""
        cat RELEASE_SUCCESS_REPORT.md | head -100
        echo ""
        echo "... 查看完整报告: cat RELEASE_SUCCESS_REPORT.md"
        ;;
    
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "✅ 发布指南完成!"
echo ""
echo "📞 如有问题:"
echo "   - 查看: RELEASE_SUCCESS_REPORT.md"
echo "   - 运行: ./COMPLETE_RELEASE_PROCESS.sh"
echo ""
