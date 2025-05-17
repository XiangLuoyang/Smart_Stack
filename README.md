# Smart Stack - 智能股票分析与决策辅助系统

## 项目介绍
Smart Stack 是一款先进的智能股票分析系统，旨在为投资者提供全面、多角度的市场洞察和决策辅助。本系统巧妙地融合了传统的**机器学习量化分析**与前沿的**大型语言模型（LLM）深度解读**，实现两种分析视角的并行展示，助您更精准地把握市场动态。

## 主要特性
- **双引擎分析**：同时提供基于机器学习的量化预测和基于LLM的深度文本分析报告。
- **机器学习模块**：
    - **趋势学习**：使用LSTM深度学习模型对股价进行短期趋势学习（注意：当前模型为每次分析时基于单只股票数据训练，其结果的泛化能力和预测精度有待进一步通过更复杂的离线训练优化）。
    - **增强技术分析**：集成 `TA-Lib` 库，自动计算并展示多种关键技术指标，包括移动平均线(MA)、相对强弱指数(RSI)、MACD、布林带(Bollinger Bands)。
    - **K线形态识别**：自动识别如十字星、锤头线、吞没形态等常见K线形态，为投资决策提供更多技术面依据。
    - **量化报告**：生成包含核心预测指标、风险评估以及结合技术信号的初步投资建议的结构化报告。
- **LLM深度分析模块**：
    - **灵活模型配置**：支持通过 `.env` 文件（基于项目中的 `envconf` 模板）轻松配置和切换不同的大型语言模型服务商及模型。
    - **全面报告生成**：LLM会综合利用实时股票数据（通过YFinance获取）进行深入分析，覆盖最新交易信息、财务指标、技术面、市场背景及风险评估，并生成专业的Markdown格式分析报告。
- **高效缓存机制**：
    - 对机器学习的预测数值和LLM生成的分析报告均实现了基于日期的本地文件缓存（存储于项目根目录下的 `.cache` 文件夹中）。
    - 同一只股票在同一天内的重复分析请求将直接从缓存加载，显著提高响应速度并节省API调用成本。
    - 缓存文件会自动清理（默认保留最近7天）。
- **用户友好界面**：基于 Streamlit 构建交互式Web应用，方便用户选择股票、调整参数并直观地查看分析结果。

## 安装与配置指南

### 1. 环境准备
- **Python版本**：推荐使用 Python 3.11 或更高版本。
- **虚拟环境（强烈推荐）**：建议为本项目创建一个独立的Python虚拟环境（例如使用 `venv` 或 `conda`），以避免包版本冲突。
  ```bash
  # 使用 venv 创建虚拟环境 (示例)
  python3 -m venv .venv
  source .venv/bin/activate # macOS/Linux
  # .venv\Scripts\activate # Windows (使用 Git Bash 或 WSL 时可能仍是 source)
  ```

### 2. 克隆项目
如果您尚未克隆项目，请执行：
```bash
# git clone https://github.com/your_username/your_project_name.git # 请替换为您的项目仓库地址
# cd your_project_name
```

### 3. 安装 TA-Lib C语言库 (关键步骤)
`TA-Lib` Python包依赖于其底层的C语言库。您必须先在您的操作系统上安装这个C库，然后才能成功安装Python包。
- **macOS**:
  ```bash
  brew install ta-lib
  ```
- **Linux (Debian/Ubuntu)**:
  ```bash
  sudo apt-get update
  sudo apt-get install -y libta-lib-dev
  ```
- **Windows**:
  安装 TA-Lib C 库在 Windows 上可能较为复杂。推荐以下方式之一：
    1.  从 [Unofficial Windows Binaries for Python Extension Packages](https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib) 下载与您Python版本和系统架构匹配的 `TA_Lib‑XYZ‑cpXYZ‑cpXYZ‑win_XYZ.whl` 文件，然后使用 `pip install TA_Lib‑XYZ‑cpXYZ‑cpXYZ‑win_XYZ.whl` 安装。
    2.  如果您使用 Anaconda/Miniconda 环境，可以尝试通过 conda-forge 安装：`conda install -c conda-forge ta-lib`。

### 4. 安装 Python 依赖包
在激活虚拟环境后，安装 `requirements.txt` 中列出的所有Python包：
```bash
pip install -r requirements.txt
```
请确保此步骤没有报错，特别是关于 `TA-Lib` 的安装。

### 5. 配置环境变量 (`.env` 文件)
本项目使用 `.env` 文件来管理API密钥和其它敏感配置。项目中提供了一个模板文件 `envconf`。
1.  **复制模板**：在项目根目录下，将 `envconf` 文件复制并重命名为 `.env`：
    ```bash
    cp envconf .env
    ```
2.  **编辑 `.env` 文件**：用您的文本编辑器打开新创建的 `.env` 文件，并填入您自己的实际配置信息。`envconf` 文件提供了所需的变量名，如下所示：
    ```env
    # envconf 模板内容 (您需要将其中的占位符替换为真实值)
    LLM_MODEL_NAME="your model name"
    LLM_API_BASE_URL="your base url"
    LLM_API_KEY="your key" 
    LLM_TEMPERATURE="0.3" # 可选

    TUSHARE_TOKEN="your tushare token"
    ```
    **重要配置说明与示例**：
    *   `TUSHARE_TOKEN`: 您在 Tushare Pro 注册获取的API Token。
    *   `LLM_MODEL_NAME`, `LLM_API_BASE_URL`, `LLM_API_KEY`: 这些用于配置您希望使用的LLM。
        *   **API密钥 (`LLM_API_KEY`) 是必需的。**
        *   如果 `LLM_MODEL_NAME` 和 `LLM_API_BASE_URL` 未在 `.env` 中设置，代码会默认使用DeepSeek的配置（但仍需您提供 `LLM_API_KEY`）。
        *   **使用OpenAI兼容端点（如阿里云通义千问）时**：`LLM_MODEL_NAME` 通常需要在模型名前加上 `openai/` 前缀。
        *   **示例 - DeepSeek (若不填则为默认，但API Key必需)**:
            ```env
            LLM_MODEL_NAME="deepseek/deepseek-chat"
            LLM_API_BASE_URL="https://api.deepseek.com/v1"
            LLM_API_KEY="YOUR_DEEPSEEK_API_KEY"
            ```
        *   **示例 - 阿里云通义千问 (Qwen) OpenAI兼容模式**:
            ```env
            LLM_MODEL_NAME="openai/qwen-turbo" # 或您使用的其他Qwen模型，如 openai/qwen-max
            LLM_API_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
            LLM_API_KEY="YOUR_DASHSCOPE_API_KEY"
            ```
    *   `LLM_TEMPERATURE` (可选): 控制模型输出的随机性，默认为0.3。
    *   `LLM_SYSTEM_PROMPT` (可选): 给LLM的系统级指令。如果不在 `.env` 中设置，代码会使用一个默认的中文金融分析师提示。您可以按需添加此行到 `.env` 中进行自定义，例如：
        ```env
        # LLM_SYSTEM_PROMPT="你是一位专注于短线交易的分析师，请提供简洁的操作建议。"
        ```
    **请务必将所有 `"your ..."` 占位符替换为您真实的API密钥和配置。** `.gitignore` 文件已配置为忽略 `.env` 文件，因此您的密钥不会被意外提交。

### 6. (可选) Docker 部署
如果您希望通过 Docker 部署：
1.  确保已安装 Docker 和 Docker Compose。
2.  **准备 `.env` 文件**：在执行 Docker 命令前，请确保已按照步骤5在项目根目录根据 `envconf` 创建并正确配置了您的 `.env` 文件。Docker Compose 配置 (`docker-compose.yml`) 会通过 `env_file` 指令引用此 `.env` 文件来注入环境变量。
3.  **Dockerfile 与 TA-Lib**: 项目中提供的 `Dockerfile` 已经内置了 TA-Lib C 语言库的完整安装步骤（通过源码编译，兼容多种架构）。您**无需**手动修改 `Dockerfile` 来添加 TA-Lib 安装指令。
4.  在项目根目录运行（如果首次运行或Dockerfile有改动，建议加上 `--build`）：
    ```bash
    docker-compose up -d --build 
    ```
    如果您希望使用特定的 `Dockerfile`（例如，如果您有多个 Dockerfile 版本），并且您的 `docker-compose.yml` 中没有明确指定 `build.dockerfile`，您可能需要先手动构建镜像，例如：
    ```bash
    # 假设您的主 Dockerfile 名为 Dockerfile.conda
    # docker build -f Dockerfile.conda -t smart-stack:custom .
    # 然后在 docker-compose.yml 中使用 image: smart-stack:custom
    ```
    通常情况下，如果您的 `docker-compose.yml` 中的 `build` 指令指向 `.` (当前目录)，并且项目根目录下有 `Dockerfile`，则 `docker-compose up --build` 会自动使用它。
5.  访问服务：浏览器打开 `http://localhost:8501` (或其他在 `docker-compose.yml` 中配置的端口)。
6.  停止服务：`docker-compose down`。
7.  **更新应用 (当源代码更新后)**：
    如果您本地的源代码（例如通过 `git pull`）更新了，并且您希望 Docker 容器也使用最新的代码，请按照以下步骤操作：
    a.  **获取最新代码**：确保您的本地项目目录已更新到最新的源代码版本。
        ```bash
        # 例如，如果您使用 Git 管理代码
        # git pull origin main  # 或者您使用的分支名
        ```
    b.  **重新构建镜像**：这一步会将最新的代码和依赖（如果 `Dockerfile` 或 `requirements.txt` 有变动）打包到新的 Docker 镜像中。
        ```bash
        docker-compose build
        ```
        或者，如果您在启动时总是使用 `--build` 选项，也可以直接执行下一步。
    c.  **重新启动服务**：`docker-compose` 会使用新构建的镜像来启动容器。
        ```bash
        docker-compose up -d
        ```
        如果您在上一步没有单独执行 `build`，确保在这里加上 `--build`：
        ```bash
        # docker-compose up -d --build
        ```
    这样，您的 Docker 化应用就会更新到最新版本。

## 使用说明
1.  确保所有环境准备、依赖安装和 `.env` 文件配置均已完成。
2.  在项目根目录的终端中（确保虚拟环境已激活），运行：
    ```bash
    streamlit run smart-trade.py
    ```
3.  系统将在浏览器中打开一个Web界面。
4.  在界面侧边栏：
    *   选择股票代码进行分析。
    *   ~~选择分析模式：“单只股票分析”、“沪深100股票分析”或“两者都进行”。~~ (功能已简化为仅单股LLM分析)
    *   ~~若选择“单只股票分析”，请选择股票代码，并可调整预测参数（这些参数主要影响机器学习部分的预测）。~~ (ML预测参数已移除)
5.  查看分析结果：
    *   对于选定的股票，主界面将展示该股票的详细数据、技术指标图表、风险指标以及LLM生成的深度分析报告。
    *   ~~机器学习和~~LLM的分析结果会利用缓存机制，当日内对同一股票的重复请求将从本地缓存加载，以提高效率。

## 项目结构
```
Smart_Stack/
├── .cache/                # 本地缓存目录 (自动生成，已被.gitignore忽略)
│   ├── llm_reports_cache/ # LLM分析报告缓存
│   └── ml_predictions_cache/ # 机器学习预测数值缓存
├── data/                  # 存放原始数据文件 (如 sz100_stocks.csv)
├── src/                   # 源代码目录
│   ├── config/            # 应用配置文件 (settings.py)
│   ├── data/              # 数据加载与处理模块 (loader.py, processor.py)
│   ├── llm_analysis/      # LLM分析核心逻辑 (core.py)
│   ├── models/            # 机器学习模型与技术指标计算 (prediction.py, risk.py, technical.py)
│   ├── tools/             # 外部工具接口 (如 financial_tools.py for YFinance)
│   └── visualization/     # 数据可视化与报告生成 (charts.py, reports.py)
├── .env                   # 环境变量配置文件 (需用户根据envconf创建并填写，被.gitignore忽略)
├── envconf                # .env文件的模板 (版本控制)
├── .gitignore             # Git忽略配置文件
├── Dockerfile             # Docker配置文件 (示例，可能需按需调整)
├── docker-compose.yml     # Docker Compose配置文件 (示例，可能需按需调整)
├── README.md              # 项目说明文件
└── requirements.txt       # Python依赖包列表
```

## 注意事项
- **TA-Lib C库**：成功运行本项目的机器学习技术分析部分，强依赖于TA-Lib C库的正确安装。
- **API密钥**：请务必保护好您的 `.env` 文件及其中包含的API密钥。
- **模型效果**：机器学习（尤其是LSTM预测）部分的效果受多种因素影响。当前版本中的LSTM为即时训练（其结果会被日度缓存），其预测精度仅供参考，主要价值在于与技术指标、LLM分析形成多维度印证。更高级的LSTM模型优化（如离线批量训练通用模型）是未来的改进方向。
- **LLM依赖**：LLM分析的质量和成本取决于您所选择和配置的LLM服务商及模型。

## 许可证
本项目采用 MIT 许可证。

## 贡献与反馈
欢迎通过提交 Issue 或 Pull Request 来帮助改进本项目。如果您在使用中遇到任何问题或有好的建议，也请不吝告知。
