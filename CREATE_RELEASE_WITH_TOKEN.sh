#!/bin/bash
# Smart Stack v1.1.0 Release创建脚本（需要GitHub Token）

set -e

echo "🚀 Smart Stack v1.1.0 GitHub Release创建脚本"
echo "="==========================================

# 检查GitHub Token
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ 未设置GITHUB_TOKEN环境变量"
    echo ""
    echo "请设置你的GitHub Token:"
    echo "  1. 访问: https://github.com/settings/tokens"
    echo "  2. 点击 'Generate new token'"
    echo "  3. 选择 'repo' 权限"
    echo "  4. 生成并复制Token"
    echo ""
    echo "然后运行:"
    echo "  export GITHUB_TOKEN=你的token"
    echo "  ./CREATE_RELEASE_WITH_TOKEN.sh"
    echo ""
    exit 1
fi

echo "✅ GitHub Token已设置"
echo ""

# 读取发布说明
RELEASE_BODY=$(cat RELEASE_NOTES_v1.1.0.md | sed 's/"/\\"/g' | sed ':a;N;$!ba;s/\n/\\n/g')

# 创建JSON数据
JSON_DATA=$(cat <<JSON
{
  "tag_name": "v1.1.0",
  "target_commitish": "main",
  "name": "Smart Stack v1.1.0 - YFinance优化版",
  "body": "$RELEASE_BODY",
  "draft": false,
  "prerelease": false,
  "generate_release_notes": false
}
JSON
)

echo "📦 正在创建Release v1.1.0..."
echo ""

# 调用GitHub API
RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Content-Type: application/json" \
  -d "$JSON_DATA" \
  https://api.github.com/repos/XiangLuoyang/Smart_Stack/releases)

# 分离响应体和状态码
HTTP_STATUS=$(echo "$RESPONSE" | tail -1)
RESPONSE_BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_STATUS" = "201" ]; then
    echo "🎉 Release创建成功!"
    echo ""
    
    # 提取Release URL
    RELEASE_URL=$(echo "$RESPONSE_BODY" | grep -o '"html_url":"[^"]*"' | cut -d'"' -f4)
    if [ -n "$RELEASE_URL" ]; then
        echo "✅ Release链接: $RELEASE_URL"
    fi
    
    # 提取Release ID
    RELEASE_ID=$(echo "$RESPONSE_BODY" | grep -o '"id":[0-9]*' | cut -d':' -f2)
    if [ -n "$RELEASE_ID" ]; then
        echo "✅ Release ID: $RELEASE_ID"
    fi
    
    echo ""
    echo "📊 发布信息:"
    echo "  - 版本: v1.1.0"
    echo "  - 目标分支: main"
    echo "  - 提交哈希: e9418b2"
    echo "  - 状态: 已发布"
    echo ""
    
    echo "🔗 访问链接:"
    echo "  https://github.com/XiangLuoyang/Smart_Stack/releases/tag/v1.1.0"
    echo ""
    
else
    echo "❌ Release创建失败 (HTTP状态码: $HTTP_STATUS)"
    echo ""
    echo "错误信息:"
    echo "$RESPONSE_BODY" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE_BODY"
    echo ""
    
    echo "💡 可能的原因:"
    echo "  1. Token权限不足（需要repo权限）"
    echo "  2. Token已过期"
    echo "  3. 网络连接问题"
    echo "  4. 仓库不存在或无权访问"
    echo ""
    
    echo "🔄 备用方案:"
    echo "  1. 手动创建: https://github.com/XiangLuoyang/Smart_Stack/releases/new"
    echo "  2. 使用GitHub CLI: gh release create v1.1.0 ..."
    echo ""
fi

echo "📋 手动创建步骤（备用）:"
echo ""
echo "1. 访问: https://github.com/XiangLuoyang/Smart_Stack/releases"
echo "2. 点击 'Draft a new release'"
echo "3. 选择标签: v1.1.0"
echo "4. 标题: Smart Stack v1.1.0 - YFinance优化版"
echo "5. 描述: 复制 RELEASE_NOTES_v1.1.0.md 内容"
echo "6. 点击 'Publish release'"
echo ""

echo "✅ 脚本执行完成"
