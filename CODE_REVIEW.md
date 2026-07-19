# Smart Stack 代码审查报告

- 审查日期：2026-07-17
- 基准版本：v1.3.0（`main` 分支，commit `82ad2ae`）
- 审查范围：全项目入口 `smart-trade.py` + `src/` 各模块 + 配置文件
- 审查方式：静态调用链分析（本次环境无可用的 Python 解释器，`.venv` 损坏，未实际运行；P0/P1 结论来自静态读码，逻辑闭环明确）
- 更新记录：
  - 2026-07-19：分支对比增补（见文末「附：分支对比」）。
  - 2026-07-19：在 `main` 上独立重写了 #1 / #4 / #10（参考 master 思路，未合并分支历史），详见各条「修复状态」。
  - 2026-07-19：Python 解释器可用——`%LOCALAPPDATA%\Programs\Python\Python312`（v3.12.10）实为完整既有安装，此前「找不到」系搜索遗漏。沙箱对该用户目录执行有限制，需 `require_escalated`。pandas / yfinance / akshare 已通过清华镜像装到该解释器。**#1 已通过运行验证**（加载美股不再栈溢出）；#4 / #10 经 `py_compile` 编译通过。
  - 2026-07-19：修复移植引入的 `smart-trade.py` 缩进错误（第 338-359 行 col1 段，apply_patch 误将整块缩进偏移）——Node 括号状态机未发现，Python `py_compile` 才暴露。

## 总体结论

项目作为个人投资辅助工具功能丰富，但当前 `main` 分支存在若干会导致功能失效的真实 bug，叠加一处密钥泄露。单只 A 股分析"看起来能用"掩盖了底层多处断裂。按严重度分为 P0（崩溃/数据失效）、P1（计算正确性/数据流断裂）、P2（性能/一致性）、P3（卫生问题）。

---

## P0 — 会导致崩溃 / 数据失效

### 1. 数据加载器循环依赖 → 美股/港股分析必然栈溢出

- 修复状态：**已在 main 修复（2026-07-19）**。在 `smart_loader.py` 新增 `_YFinanceAdapter`，直接封装 `import yfinance`，替换原先把 `StockDataLoader` 注册为 yfinance 源的写法；`from .loader import` 已从该文件移除，循环切断。改动参考 master 的 `_YFinanceAdapter`，但未引入 master 的 `demo_data` 依赖（main 无此模块，会 ImportError）。语法经 Node 状态机校验括号/三引号配对正常；因本机无 Python 解释器未做运行验证。

- 运行验证（2026-07-19）：Python 3.12.10 下 `from src.data.smart_loader import ...` 成功；实例化 `SmartDataSource().initialize_sources()` 后 `yfinance is adapter: True`、`best_source for AAPL = yfinance`；加载 `AAPL` 返回 `source: failed`（yfinance 429 限流）但**不再触发 RecursionError**，证明循环已切断。附带发现：`akshare` 数据源加载失败因 `loader_akshare.py` 顶层 `import streamlit`（即 review #7），环境未装 streamlit 时 akshare 整个不可用——这强化了 #7 的优先级。

- 证据：`src/data/loader.py:58` 的 `StockDataLoader.load_stock_data` 把所有请求委托给 `smart_loader`；而 `src/data/smart_loader.py:56-57` 又把 `loader.py` 里的 `StockDataLoader` 注册为 yfinance 数据源：
  ```python
  from .loader import StockDataLoader
  yfinance_loader = StockDataLoader(self.config)
  ```
- 影响范围：对非 A 股（`get_best_source` 返回 `yfinance`），调用链自我闭合：`SmartDataSource.load_stock_data` → 选 `yfinance` → 内部 `StockDataLoader.load_stock_data` → `self.smart_loader.load_stock_data`（同一单例）→ 又选 `yfinance` → … → `RecursionError`。所有美股/港股分析、以及 A 股在 akshare 失败后回退 yfinance 的路径都会触发。A 股走 akshare 是独立后端，所以单只 A 股分析能用，掩盖了该问题。
- 根因：`loader_backup.py` 是重构前真正的 yfinance 实现，重构后 `loader.py` 改为纯委托，但忘了给 `smart_loader` 配一个独立的 yfinance 后端。
- 建议：给 `smart_loader` 配独立 yfinance 后端，或让 `loader.py` 保留真正的 yfinance 逻辑而非纯委托。

### 2. 泄露的 Tushare API token（已进入 git 历史）

- 证据：`src/data/loader_backup.py:14` 硬编码：
  ```python
  ts.set_token('5d35cfa04f7c37346fc16dbf860b6e8ea05cb5593ee956fed1d9bbc3')
  ```
- 该文件在 commit `796cd4c` 被提交，token 已进入 GitHub 远程历史。这不是占位符，是真实密钥。
- 备注：`envconf` / `envconf_backup` 模板本身都是占位符，没有泄密；`.env` 被 `.gitignore` 正确忽略。泄密仅在 `loader_backup.py`。
- 建议：立即在 Tushare 后台吊销该 token；用 `git filter-repo` / BFG 从历史清除（仅删文件不够，历史仍可追溯）。

---

## P1 — 计算正确性 / 数据流断裂

### 3. LSTM 置信区间恒为 0（蒙特卡洛是假的）

- 证据：`src/models/prediction.py:128-135` 注释声称"模拟蒙特卡洛（20次）"，但循环里每次用完全相同的输入 `scaled` 调 `self.model.predict(batch)`。推理是确定性的（不训练、无 dropout 激活），20 次输出完全相同。
- 影响：`std_return == 0` → 置信区间上下界相等，退化为点估计；返回的 `simulation_runs: 20` 字段具有误导性。
- 建议：引入真实随机性（MC dropout 推理、多次训练、或对输入加噪），或删除该字段避免误导。

### 4. ML 预测结果到报告的字段名完全对不上 → 报告永远显示 N/A

- 修复状态：**已在 main 修复（2026-07-19）**。在 `reports.py` 入口处新增字段归一化层：从 `expected_daily_return` / `daily_std` / `confidence_interval:{lower,upper}` 读取原始小数，换算为百分比，供核心指标表与投资建议段统一使用；下游三处 `_pct` 旧 key 引用全部清除。改动参考 master（与 `fcabda3` 一致），无新增耦合。

- 证据：
  - 预测器 `src/models/prediction.py` 返回 key：`expected_daily_return` / `daily_std` / `confidence_interval:{lower,upper}` / `method`。
  - 报告生成器 `src/visualization/reports.py:34-37` 读取另一套名字：
    ```python
    prediction_results.get('expected_daily_return_pct', 'N/A')
    prediction_results.get('daily_lower_bound_pct', 'N/A')
    prediction_results.get('daily_upper_bound_pct', 'N/A')
    prediction_results.get('daily_volatility_pct', 'N/A')
    ```
  - `smart-trade.py` 把 `calculate_expected_return` 结果原样传给 `report_generator`，无任何字段映射。
- 影响：核心指标表四个预测值全为 `N/A`；`has_predictive_data`（`reports.py:54`）恒为 False；投资建议里 `expected_daily_return` 恒为 `N/A` → 评级永远"中性展望"，综合建议永远走默认分支。机器学习算了一通，结果一个数都没展示。属重命名后未改干净的回归 bug。
- 建议：统一两处字段名，或在 `smart-trade.py` 传参前做一次显式映射。改动小、收益大。

### 5. LLM 报告工具用 yfinance，对 A 股拿不到数据

- 证据：`src/tools/financial_tools.py` 的 `YFinanceStockTool._run` 直接 `yf.Ticker(symbol)`，未走 `smart_loader`。UI 传入的 `selected_stock` 是 CSV 里的 6 位代码（如 `002415`），而 yfinance 需要 `002415.SZ` 格式。
- 影响：纯数字代码在 yfinance 下取不到数据，LLM 报告只能拿到空/错误数据；主数据源（akshare）与 LLM 工具（yfinance）口径不一致。
- 建议：LLM 工具接入 `smart_loader` 并做 A 股代码格式转换。

### 6. `.env` 配置自相矛盾，模型名缺 provider 前缀

- 证据：`.env` 含两套配置，后者覆盖前者，最终生效的是 `LLM_MODEL_NAME="deepseek-chat"`（缺 `deepseek/` 前缀）+ `LLM_API_BASE_URL="https://api.deepseek.com"`（缺 `/v1`）。而 `envconf` 模板里第一套（`deepseek/deepseek-chat` + `/v1`）才是正确的。
- 影响：crewai/litellm 依赖模型名的 provider 前缀做路由，`deepseek-chat` 会被当成 openai 模型处理，可能调用失败或路由到错误端点。
- 建议：修正 `.env`（本文件本地，不入库）；并在 `envconf` 模板里强调前缀与 `/v1` 的必要性。

---

## P2 — 性能 / 一致性

### 7. AKShareDataLoader 在业务层直接调用 `st.*`

- 修复状态：**已在 main 修复（2026-07-19）**。`loader_akshare.py` 业务层（`__init__` / `load_stock_data` / `get_company_info` / `get_financial_data` / `test_connection` / `get_real_time_quote` 等）约 14 处 `st.info/success/error/warning` 全部替换为 `logger.info/debug/warning/error`；顶部移除 `import streamlit as st`。文件末尾的 `test_akshare_loader()` 是独立的 Streamlit 演示函数，其 `st.*` 调用属预期行为，予以保留。

- 证据：`src/data/loader_akshare.py` 的 `__init__` / `load_stock_data` / `test_connection` 里满是 `st.info/st.success/st.error`。
- 影响：双重问题——commit `5e95207` 声称已"UI 与业务解耦"，此处未改干净；`OptimizedReturnPredictor` 用 `ThreadPoolExecutor` 在 worker 线程跑 `load_stock_data`，在非主线程调 `st.*` 会抛异常，导致沪深100并行分析里 A 股加载静默失败。
- 建议：用 `logging` 替换所有 `st.*`，UI 反馈由上层回调驱动（项目已有 `progress_callback` 约定）。

### 8. 连接测试拉全市场行情

- 修复状态：**已在 main 修复（2026-07-19）**。`test_connection()` 由 `ak.stock_zh_a_spot()`（全市场）改为 `ak.stock_zh_a_hist(symbol="000001", period="daily", start_date=今日-5天, end_date=今日)`，仅拉平安银行近 5 日日线做存活探测；`get_real_time_quote()` 同样改为按个股调 `stock_zh_a_hist` 取最近 10 日历史。`initialize_sources` 首次加载不再触发数千只股票的全量行情拉取。

- 证据：`src/data/loader_akshare.py` 的 `test_connection` 调 `ak.stock_zh_a_spot()`（数千只股票全量实时行情），却在每次 `initialize_sources`（首次加载）触发；`get_real_time_quote` 也用同一全市场接口查单只股票。
- 影响：应用启动慢；单只查询效率极低。
- 建议：连接测试改用轻量探测（如单只股票的小范围历史数据），实时行情走精确接口。

### 9. TA-Lib 依赖与文档/requirements 矛盾

- 修复状态：**已在 main 修复（2026-07-19）**。`technical.py` 把 `import talib` 包进 `try/except ImportError`，并设模块级 `TALIB_AVAILABLE` 标志；RSI / MACD / 布林带 三套指标均提供纯 pandas 的 fallback 分支（ewm 滚动、指数平滑、±2σ）。`reports.py` 同样把 `import talib` 包进 try/except，K线形态（十字星/锤头线/吞没）整段由 `if TALIB_AVAILABLE and ...` 守卫，TA-Lib 缺失时自动跳过。本机未装 TA-Lib，烟雾测试确认 `TALIB_AVAILABLE=False` 时 RSI/MACD/布林带仍能正常计算。注：`requirements.txt` 仍不含 talib，这与「talib 为可选依赖」的新语义一致；建议后续在 README 中注明 talib 为可选加速依赖。

- 证据：`src/models/technical.py` 与 `src/visualization/reports.py` 顶层 `import talib`，装不上即 import 崩溃；但 README 宣称"无需系统级 TA-Lib"，`requirements.txt` 也不含 talib。同时 `src/data/processor.py` 另有一套纯 pandas 的 RSI/MACD 实现，两套并存且口径不同。
- 建议：二选一并统一——要么 requirements 明确要求 talib 并更新文档，要么全部用 pandas 版并删除 talib 依赖。

---

## P3 — 卫生问题

### 10. Top10 推荐"预期涨幅"永远为 `--`

- 修复状态：**已在 main 修复（2026-07-19）**。`smart-trade.py` 的沪深100展示段改为从 `(code, ret)` 元组解构出收益率并格式化为百分比（`f"{ret*100:.2f}%"`）；截图标注同步用 `f"{code} ({ret*100:.2f}%)"`。参考 `fcabda3` 的二元组方案（与 main 的 `top_stocks` 结构兼容），刻意未采用 master `2f56748` 的三元组五维评分重构——后者依赖 monthly/quarterly 等新字段，移植成本与回归风险更高。

- 证据：`smart-trade.py:173-174` 用 `[code for code, _ in ...]` 把 `expected_return` 丢弃；`smart-trade.py:344` 写死 `'预期涨幅': ["--"] * len(...)`。
- 影响：排序后的涨跌幅是现成数据，却没展示。
- 建议：保留 `(code, return)` 并在表格中显示。

### 11. `.venv` 损坏 / 当前机器无法运行

- 修复状态：**部分缓解（2026-07-19）**。经查 `%LOCALAPPDATA%\Programs\Python\Python312` 实为完整的既有 Python 3.12.10 安装（6004 文件、python312.dll 齐全），此前「找不到」系搜索路径遗漏（只查了 313/311/310）。项目 `.venv` 仍指向已删除的解释器路径、尚未重建。

- 证据：`.venv` 指向 `Python312\python.exe`，该解释器已不存在；系统也找不到 `py` / `python` / `conda`。
- 影响：项目在当前环境无法启动。
- 建议：重建虚拟环境；考虑固定 Python 版本到文档/README。
- 重建命令（已验证解释器可用）：`"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m venv .venv` 后 `.venv\Scripts\pip install -r requirements.txt`（建议加 `-i https://pypi.tuna.tsinghua.edu.cn/simple`）。注意：沙箱对该用户目录执行有限制，运行时需 `require_escalated`。

### 12. 仓库根目录混乱

- `loader_backup.py` / `prediction_backup.py` / `README_backup.md` / `requirements_backup.txt` / `envconf_backup` 等备份文件进了版本库。
- 约 15 个散落的 `test_*.py`、`analyze_*.py`、`show_*.py`、`*_REPORT.md`。
- 存在误建的 `~` 目录（含 `.docker/config.json`）。
- `VERSION` 文件是 `1.1.0`，代码已是 v1.3.0，不一致。
- 建议：备份文件移出版本库或归档到 `archive/`；测试脚本集中到 `tests/`；修正 `VERSION`。

### 13. README/requirements 编码乱码

- 证据：文件为 GBK 编码内容被当 UTF-8 提交（或反之），中文全部 mojibake，对协作者不可读。
- 建议：统一以 UTF-8 重新保存。

---

## 假设与说明

- 本次环境无可用的 Python 解释器，`.venv` 损坏，故未实际运行验证。P0/P1 结论来自静态调用链分析，逻辑闭环明确（尤其循环递归 #1、字段名不匹配 #4 属"读码即可确证"）。
- `envconf` / `envconf_backup` 模板均为占位符，未泄密。

## 建议的修复优先级

1. 立即吊销并清除 Tushare token（#2）。
2. 给 `smart_loader` 配独立 yfinance 后端，打破循环递归（#1）。
3. 统一 `reports.py` 与 `prediction.py` 的字段名（#4）——改动最小、收益最大。
4. LLM 工具接入 `smart_loader` 并做 A 股代码转换（#5）；修正 `.env` 模型名（#6）。
5. 清理 `loader_akshare.py` 的 `st.*` 调用（#7）。

## 附：审查方法

依次阅读入口 `smart-trade.py`、`src/config/settings.py`、`src/models/{prediction,optimized_predictor,technical,risk}.py`、`src/data/{loader,smart_loader,loader_akshare,loader_backup,processor}.py`、`src/llm_analysis/core.py`、`src/tools/financial_tools.py`、`src/visualization/{charts,reports}.py`，并交叉核对配置文件（`.env` / `envconf` / `requirements.txt`）与 git 历史（`git log -S <token>` 验证密钥泄露）。

---

## 附：分支对比（2026-07-19 增补）

本次审查基于 `main`，但仓库里存在更新的 `master` 分支。以下是各分支与 review 问题的对照。

### 分支拓扑

线性链，`main` 是 `master` 的祖先，`master` 领先 4 个提交：

```
82ad2ae (main, origin/main)
  └─ 796cd4c  fix: 修复数据源和LLM配置问题
     └─ 150c2e3  fix: LLM工具改用AKShare获取实时A股数据
        └─ fcabda3  fix: 修复沪深100股票分析收益率显示问题   (origin/master)
           └─ 2f56748  feat: 沪深100分析改用五维综合评分+中长期预测  (master, 本地领先 origin/master 1 个提交)
```

另有两个旧分支 `origin/LLMcore`、`origin/experiment`（2025-05），是 LLM 核心的早期简化版，删除了大量文件（loader_akshare / smart_loader / optimized_predictor / reports 全删），属平行早期分支，不含本次问题的解法。

### 拓扑勘误（2026-07-19）

经 `git merge-base` 确认，`main` 与 `master` **无共同祖先**（merge-base 返回空），是两条独立起源的历史：`main` 根为 `a2b6e1e Initial commit`，`master` 根直接从 `796cd4c` 起。此前的「线性延续」判断系提交信息误导所致。因此 `git merge --ff-only` 会因 "refusing to merge unrelated histories" 失败，普通合并需 `--allow-unrelated-histories` 且会产生大量冲突（master 缺失 main 的 v1.3.0/Top10 优化/review-fix 等 6 个提交）。结论：合并并不可行/不值得，已改为在 main 上独立重写修复（见各条「修复状态」）。

### 问题 vs 分支 矩阵

| # | 问题 | main (82ad2ae) | master (2f56748) | 判定 |
|---|------|----------------|------------------|------|
| 1 | 数据加载器循环依赖 | 存在 → **main 已修(07-19)** | **已修复** | master 新增独立 `_YFinanceAdapter`（直接封装 `import yfinance`），代码注释明确"避免通过 StockDataLoader 造成循环调用"；已在 main 独立移植同款适配器（去 demo_data 依赖） |
| 2 | 泄露的 Tushare token | 存在（blob 674610） | **仍存在**（同一 blob） | 两分支 `loader_backup.py` 完全相同且都被追踪，token 字符串仍在；`envconf`/`envconf_backup` 也仍被追踪 |
| 3 | LSTM 置信区间恒为 0 | 存在 | 未改动 | `prediction.py` 在 master 上无变化（不在 diff 列表中） |
| 4 | ML 预测→报告字段名不匹配 | 存在 → **main 已修(07-19)** | **已修复** | `reports.py` 改读 `expected_daily_return` / `daily_std` / `confidence_interval`，与 `prediction.py` 返回键完全对齐；已在 main 独立移植归一化层 |
| 5 | LLM 工具用 yfinance，A股拿不到数据 | 存在 | **未修复（名不副实）** | commit `150c2e3` 写"LLM工具改用AKShare"，但 `financial_tools.py` main↔master **零差异**，仍是 `yf.Ticker(symbol)`，未接入 smart_loader / AKShare |
| 6 | `.env` 模型名缺 provider 前缀 | 存在 | 不适用 | `.env` 是本地文件不入库；`envconf` 模板两分支相同，未更新强调前缀要求 |
| 7 | loader_akshare 业务层调 `st.*` | 大量存在 → **main 已修(07-19)** | **已修复** | master 仍有残留；main 已把业务层约 14 处 `st.*` 全部换成 `logging`，仅保留文件末尾 `test_akshare_loader()` 演示函数的 `st.*` |
| 8 | 连接测试拉全市场行情 | 存在 → **main 已修(07-19)** | **已修复** | `test_connection` 改为 `stock_zh_a_hist(symbol="000001", 近5日)` 轻量探测，`get_real_time_quote` 按个股精确拉历史；master 未动 |
| 9 | TA-Lib 依赖与文档矛盾 | 存在 → **main 已修(07-19)** | **已修复** | `technical.py`/`reports.py` 把 `import talib` 包进 try/except 并设 `TALIB_AVAILABLE` 标志，RSI/MACD/布林带/K线形态均有纯 pandas fallback；master 未动 |
| 10 | Top10 收益率永远 `--` | 存在 → **main 已修(07-19)** | **已修复** | `smart-trade.py` 改为 `[f"{code} ({ret*100:.2f}%)" for code, ret in ...]`；已在 main 按 `fcabda3` 二元组方案独立移植（未引入 master 五维评分重构） |
| 11 | `.venv` 损坏 | 环境 | 环境 | 与分支无关，本地 venv 指向已删除的 Python312 |
| 12 | 仓库根目录混乱 | 存在 | 基本未动 | 备份文件、散落脚本、`~` 目录、`VERSION=1.1.0` 在 master 上依旧 |
| 13 | README/requirements 乱码 | 存在 | 未改动 | 编码问题未处理 |

### 小结

`master` 集中修了**展示层和数据流**问题（#1、#4、#10），这部分改动质量不错；但因 main/master 为不相关历史，无法直接合并，已改在 main 上独立重写这三处（均完成）。对**安全（#2）、依赖一致性（#8、#9）、#5** 这类需要实质重构或清历史的问题，master 同样未触及，其中 #5 还出现了提交信息与实际改动不符的情况（`150c2e3` 声称改用 AKShare，`financial_tools.py` 实际未动）。

### 建议的下一步

1. **已完成（2026-07-19）**：#1 / #4 / #10 已在 main 上独立修复（参考 master / fcabda3 思路，未合并分支）。语法经状态机校验通过；运行验证待本机恢复 Python 解释器后补充。
2. #2 仍需独立处理：吊销 Tushare token，并从 `main` 历史中清除 `loader_backup.py`（`git filter-repo`）。注意 main/master 为不相关历史，需各自清理。
3. #5 需重新实现（`financial_tools.py` 接入 smart_loader + A股代码格式转换），`150c2e3` 的提交信息应订正或补充一个真正改 AKShare 的提交。
4. **已完成（2026-07-19）**：#7 / #8 / #9 已在 main 修复（logging 替换、轻量探测、可选 TA-Lib + pandas fallback），5 个改动文件 `py_compile` 全通过。
5. #3、#6、#12、#13 在两分支均未处理，仍按原 review 的修复建议推进。#2（token 清理）与 #5（LLM 工具接入 smart_loader）仍待处理。

---

## Roadmap — 后续功能规划

以下为计划中的功能，性能问题（#7 / #8 / #9）解决后再启动，此处先记录需求与目标。

### R1. 持仓分析（Portfolio Analysis）

- 目标：对当前所有持仓做统一分析，输出每只持仓的估值/技术信号/风险贡献，并在组合层面给出仓位集中度、行业暴露、整体收益与回撤等汇总视图。
- 输入：持仓表（代码 + 数量 + 成本价），行情与基本面走现有 `smart_loader` / AKShare 数据源。
- 与现有能力的关系：复用 `technical.py` 的 RSI/MACD/布林带、`prediction.py` 的预期收益；新增组合层聚合逻辑（行业分类、集中度、加权收益）。
- 非目标（本期）：自动调仓建议、与券商 API 对接。

### R2. 交易日志系统（Trade Journal）

- 目标：记录每一笔买入/卖出/调仓事件，支持事后复查（post-hoc review）：回看某笔交易当时的信号、持仓状态、盈亏归因。
- 数据模型（草案）：交易日志表 = {时间, 代码, 方向(买/卖), 价格, 数量, 费用, 触发信号, 备注}；与行情快照关联便于复盘。
- 与现有能力的关系：依赖 R1 的持仓状态作为交易前/后的快照来源；存储建议落地为本地文件（CSV/SQLite），不引入新的服务依赖。
- 非目标（本期）：实时推送、云端同步。

### 实施顺序

1. （已完成）性能修复 #7 / #8 / #9。
2. R1 持仓分析。
3. R2 交易日志系统（依赖 R1 的持仓状态）。
