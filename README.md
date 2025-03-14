# Smart Stack - 智能股票分析系统

## 项目介绍
Smart Stack是一个基于人工智能和技术分析的智能股票分析系统。该系统集成了多种分析方法，包括缠论分析、LSTM预测模型和技术指标分析，为投资者提供全面的市场洞察和交易建议。

## 主要功能
- **缠论分析**：基于缠论理论的市场结构分析，识别趋势和关键支撑阻力位
- **智能预测**：使用LSTM深度学习模型预测股票走势
- **风险评估**：计算波动率、最大回撤和夏普比率等风险指标
- **技术分析**：提供常用技术指标分析
- **股票筛选**：基于多维度分析推荐买入和卖出标的

## 安装说明

### 方式一：本地安装
1. 克隆项目代码：
```bash
git clone https://github.com/Xiangluoyang/Smart_Stack.git
cd Smart_Stack
```

2. 安装依赖包：
```bash
pip install -r requirements.txt
```

3. 配置Tushare API：
在使用系统前，需要先注册[Tushare Pro](https://tushare.pro/)账号并获取API token。

### 方式二：Docker部署
1. 确保已安装Docker和Docker Compose

2. 克隆项目并进入目录：
```bash
git clone https://github.com/XiangLuoyang/Smart_Stack.git
cd Smart_Stack
```

3. 使用Docker Compose启动服务：
```bash
docker-compose up -d
```

4. 访问服务：
打开浏览器访问 http://localhost:8501

5. 停止服务：
```bash
docker-compose down
```

## 使用说明
1. 启动系统：
```bash
streamlit run smart-trade.py
```

2. 系统功能：
- 在Web界面选择要分析的股票代码
- 设置分析参数（时间范围、置信度等）
- 查看分析结果和可视化图表

## 项目结构
```
smart_stack/
├── src/                # 源代码目录
│   ├── config/        # 配置文件
│   ├── data/          # 数据处理模块
│   ├── models/        # 分析模型
│   ├── visualization/ # 可视化模块
│   └── utils/         # 工具函数
├── data/              # 数据文件
└── requirements.txt   # 项目依赖
```

## 注意事项
- 使用前请确保已正确配置Tushare API token
- 建议使用Python 3.8或更高版本
- 首次运行可能需要下载模型权重文件

## 许可证
MIT License

## 贡献指南
欢迎提交Issue和Pull Request来帮助改进项目。
