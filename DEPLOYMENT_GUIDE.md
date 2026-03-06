# Smart Stack 部署指南（YFinance版本）

## 🚀 快速部署

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
# 安装Python依赖
pip install -r requirements.txt

# 注意：无需安装系统级TA-Lib库
# YFinance已内置技术指标功能
```

### 3. 配置环境
```bash
# 复制配置模板
cp envconf .env

# 编辑.env文件，仅需配置LLM API密钥
# 数据源使用YFinance，无需额外配置
```

**最小配置示例：**
```env
# 必需：LLM API密钥
LLM_API_KEY="sk-your-deepseek-api-key"

# 可选：LLM模型配置（默认使用DeepSeek）
# LLM_MODEL_NAME="deepseek/deepseek-chat"
# LLM_API_BASE_URL="https://api.deepseek.com/v1"
```

### 4. 启动应用
```bash
streamlit run smart-trade.py
```
访问 http://localhost:8501

## 📊 数据源支持

### 支持的股票格式
| 市场 | 示例代码 | 说明 |
|------|----------|------|
| **A股** | `000001.SZ` | 平安银行（深交所） |
| **A股** | `600000.SS` | 浦发银行（上交所） |
| **A股** | `510300.SH` | 沪深300ETF |
| **美股** | `AAPL` | 苹果公司 |
| **美股** | `GOOGL` | 谷歌 |
| **港股** | `0700.HK` | 腾讯控股 |
| **ETF** | `SPY` | SPDR标普500ETF |

### 智能代码识别
- `000001` → 自动识别为 `000001.SZ`
- `600000` → 自动识别为 `600000.SS`
- `510300` → 自动识别为 `510300.SH`
- 支持6位纯数字代码自动补全后缀

## 🔧 功能验证

### 快速测试
```bash
# 运行功能测试
python test_yfinance_fix.py

# 或使用快速验证
python quick_verify.py
```

### 手动测试
1. 启动应用后，在侧边栏选择"单只股票分析"
2. 输入测试代码：`000001.SZ`、`AAPL`、`0700.HK`
3. 查看数据获取和分析结果

## 🐳 Docker部署（可选）

### 使用现有Docker配置
```bash
# 构建镜像（已更新为YFinance版本）
docker-compose build

# 启动服务
docker-compose up -d

# 访问应用
# http://localhost:8501
```

### 更新Docker镜像
如果需要更新Dockerfile以移除TA-Lib：
```dockerfile
# 在Dockerfile中移除TA-Lib安装步骤
# 只需保留Python依赖安装
RUN pip install -r requirements.txt
```

## ⚡ 性能优化

### 缓存机制
- 数据按日期缓存在 `.cache/` 目录
- 同一股票当日重复分析使用缓存
- 自动清理7天前的缓存文件

### 网络优化
- YFinance数据有本地缓存
- 支持批量数据加载
- 内置重试机制

## 🔄 从旧版本升级

### 升级步骤
1. **备份配置**：复制 `.env` 文件
2. **更新代码**：`git pull origin main`
3. **清理环境**：删除旧虚拟环境，创建新环境
4. **安装依赖**：`pip install -r requirements.txt`
5. **验证功能**：运行测试脚本

### 配置变更
- **移除**：`TUSHARE_TOKEN` 配置项
- **保留**：`LLM_API_KEY` 等LLM配置
- **新增**：智能代码识别功能

## 🛠️ 故障排除

### 常见问题

#### Q1: 数据获取失败
```bash
# 检查网络连接
ping api.finance.yahoo.com

# 检查代码格式
# 正确：000001.SZ, AAPL, 0700.HK
# 错误：000001, AAPL.US, 00700
```

#### Q2: LLM分析失败
```bash
# 检查.env文件
cat .env

# 验证API密钥
# 确保LLM_API_KEY配置正确
```

#### Q3: 依赖安装失败
```bash
# 更新pip
pip install --upgrade pip

# 单独安装失败包
pip install yfinance
pip install tensorflow
```

#### Q4: 内存不足
```bash
# 减少分析股票数量
# 调整LSTM模型参数
# 增加系统内存
```

### 日志查看
```bash
# Streamlit日志
streamlit run smart-trade.py --logger.level debug

# 查看缓存目录
ls -la .cache/
```

## 📈 监控与维护

### 健康检查
```bash
# 检查数据源连通性
python -c "import yfinance as yf; print(yf.Ticker('AAPL').history(period='1d').shape)"

# 检查LLM连通性
python -c "from openai import OpenAI; client = OpenAI(api_key='your-key'); print('Connected')"
```

### 定期维护
1. **清理缓存**：手动删除 `.cache/` 目录
2. **更新依赖**：`pip install --upgrade -r requirements.txt`
3. **备份配置**：备份 `.env` 文件
4. **检查日志**：查看错误日志

## 🎯 最佳实践

### 开发环境
1. 使用虚拟环境隔离依赖
2. 定期更新requirements.txt
3. 编写单元测试
4. 使用版本控制

### 生产环境
1. 使用Docker容器化部署
2. 配置反向代理（Nginx）
3. 设置监控告警
4. 定期备份数据

### 性能调优
1. 调整LSTM模型参数
2. 优化缓存策略
3. 使用CDN加速静态资源
4. 数据库优化（如需要）

## 🤝 获取帮助

### 问题反馈
- GitHub Issues: https://github.com/XiangLuoyang/Smart_Stack/issues
- 检查现有Issue是否已有解决方案

### 社区支持
- 提交Pull Request
- 分享使用经验
- 报告Bug

### 文档更新
- 查看最新README.md
- 关注项目更新日志
- 参与文档改进

---
**开始使用全新的Smart Stack，享受简化的部署体验！** 🚀
