# Smart Stack - 智能股票分析与决策辅助系统

## 🚀 项目简介
Smart Stack 是一款融合传统机器学习量化分析与前沿大语言模型（LLM）深度解读的智能股票分析系统。通过双引擎并行分析，为投资者提供多维度的市场洞察与决策支持。

## ✨ 核心特性

### 🤖 双引擎智能分析
- **机器学习量化引擎**：基于LSTM的短期趋势预测 + TA-Lib技术指标分析
- **LLM深度解读引擎**：大语言模型对市场数据的深度分析与报告生成
- **并行展示**：两种分析视角同步呈现，交叉验证投资信号

### 📊 机器学习模块
- **趋势预测**：LSTM深度学习模型进行短期股价趋势学习
- **技术分析**：集成TA-Lib，支持MA、RSI、MACD、布林带等20+技术指标
- **K线形态识别**：自动识别十字星、锤头线、吞没形态等常见形态
- **量化报告**：结构化输出包含预测指标、风险评估、投资建议

### 🧠 LLM深度分析模块
- **灵活配置**：支持OpenAI兼容的各类LLM模型（DeepSeek、通义千问等）
- **全面分析**：覆盖实时数据、财务指标、技术面、市场背景、风险评估
- **专业报告**：生成Markdown格式的深度分析报告

### ⚡ 高效缓存机制
- **本地文件缓存**：机器学习预测值和LLM报告按日期缓存
- **智能去重**：同一股票当日重复分析直接从缓存加载
- **自动清理**：默认保留最近7天缓存，平衡存储与性能

### 🎨 用户友好界面
- **Streamlit构建**：交互式Web应用，零配置启动
- **直观操作**：股票选择、参数调整、结果查看一站式完成
- **响应式设计**：适配桌面和移动端浏览

## 🔄 重要更新（2026-03-06）

### 数据源优化
- **已切换至YFinance**：移除Tushare依赖，无需API Token
- **多市场支持**：A股、美股、港股统一数据接口
- **安装简化**：无需系统级TA-Lib库安装
- **开箱即用**：配置更简单，启动更快

### 兼容性说明
- ✅ 原有功能完全保留
- ✅ 数据格式向后兼容
- ✅ 缓存机制继续有效
- ✅ 所有分析模块正常运作

## 🛠️ 快速开始

### 1. 环境准备
```bash
# 克隆项目
git clone git@github.com:XiangLuoyang/Smart_Stack.git
cd Smart_Stack

# 创建虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
```

### 2. 安装依赖（已简化）
```bash
# 安装Python依赖（已简化，无需系统级TA-Lib）
pip install -r requirements.txt
```
```bash
# 安装TA-Lib系统依赖
# macOS
brew install ta-lib

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y libta-lib-dev

# Windows：从 https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib 下载对应whl文件

# 安装Python依赖
pip install -r requirements.txt
```

### 3. 配置环境变量
```bash
# 复制配置模板
cp envconf .env

# 编辑.env文件，填入您的API密钥
# 必需配置：
# - LLM_API_KEY：LLM服务API密钥（如 DeepSeek）
```

**配置示例（DeepSeek）：**
```env
LLM_MODEL_NAME="deepseek/deepseek-chat"
LLM_API_BASE_URL="https://api.deepseek.com/v1"
LLM_API_KEY="your-deepseek-api-key"
```

> **注意**：数据源已从 Tushare 切换至 YFinance，无需 TUSHARE_TOKEN。

### 4. 启动应用
```bash
streamlit run smart-trade.py
```
访问 http://localhost:8501 开始使用

## 🐳 Docker部署（可选）
```bash
# 一键部署
docker-compose up -d --build

# 访问服务
# 浏览器打开 http://localhost:8501

# 停止服务
docker-compose down

# 更新代码后重新部署
docker-compose up -d --build
```

## 📖 使用指南

### 单只股票分析
1. 在侧边栏选择"单只股票分析"模式
2. 输入或选择股票代码（如：000001.SZ）
3. 调整预测参数（可选）
4. 查看分析结果：
   - 实时股价数据
   - 技术指标图表
   - LSTM趋势预测
   - LLM深度分析报告

### 沪深100分析
1. 选择"沪深100股票分析"模式
2. 系统自动分析沪深100成分股
3. 查看Top10推荐列表
4. 点击任意股票查看详细分析

### 缓存机制说明
- 首次分析会调用API进行计算
- 同一天内重复分析同一股票直接从缓存读取
- 缓存文件存储在 `.cache/` 目录
- 自动清理7天前的缓存

## 🏗️ 项目架构
```
Smart_Stack/
├── src/                    # 源代码
│   ├── config/            # 应用配置
│   ├── data/              # 数据加载与处理
│   ├── llm_analysis/      # LLM分析核心
│   ├── models/            # 机器学习模型
│   ├── tools/             # 外部工具接口
│   └── visualization/     # 可视化与报告
├── .cache/                # 缓存目录（自动生成）
├── data/                  # 静态数据文件
├── smart-trade.py         # 主程序入口
├── requirements.txt       # Python依赖
├── Dockerfile             # Docker配置
├── docker-compose.yml     # Docker Compose配置
├── .env                   # 环境配置（用户创建）
└── envconf                # 环境配置模板
```

## ⚠️ 重要说明

### 技术依赖
- **TA-Lib C库**：必须正确安装系统级TA-Lib库
- **Python 3.11+**：推荐使用Python 3.11或更高版本
- **API密钥**：需要Tushare Pro和LLM服务的有效API密钥

### 模型效果
- **LSTM预测**：当前为即时训练模型，预测结果仅供参考
- **LLM分析**：分析质量取决于所选模型和服务商
- **风险提示**：所有分析结果仅供参考，不构成投资建议

### 性能优化
- 缓存机制显著减少API调用和计算时间
- 支持Docker部署，环境隔离更稳定
- 代码模块化设计，便于扩展和维护

## 🔄 更新与维护

### 代码更新
```bash
# 拉取最新代码
git pull origin main

# 重新安装依赖（如有变更）
pip install -r requirements.txt

# Docker用户重新构建
docker-compose up -d --build
```

### 缓存管理
- 缓存自动清理：保留最近7天数据
- 手动清理：删除 `.cache/` 目录
- 缓存验证：系统会自动检测数据有效性

## 📄 许可证
本项目采用 MIT 许可证 - 详见 LICENSE 文件

## 🤝 贡献指南
欢迎贡献代码、报告问题或提出建议：

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📞 支持与反馈
- **问题报告**：[GitHub Issues](https://github.com/XiangLuoyang/Smart_Stack/issues)
- **功能建议**：通过Issues提交
- **技术讨论**：欢迎提交Pull Request

## 🎯 项目愿景
Smart Stack 致力于成为个人投资者最实用的智能分析工具，通过技术创新降低投资分析门槛，让数据驱动的投资决策更加简单、可靠。

---
**开始使用 Smart Stack，让智能分析为您的投资决策赋能！** 🚀
