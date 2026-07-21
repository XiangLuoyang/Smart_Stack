# Smart Stack 操盘工作台

A 股纸面操盘工作台:账户 / 持仓 / 订单 / 撮合 / 风控 / 回测 / 信号源一体化。前端 React + AntD + TradingView Lightweight Charts,后端 FastAPI + SQLAlchemy + SQLite + APScheduler。

> 本工作台是**纸面交易(paper trading)**:不接真实券商,资金风险为零,用于策略验证、决策演练、回测复盘。

## 功能

- **账户管理**:多虚拟账户,初始资金自定义,实时浮动盈亏
- **下单**:市价 / 限价,买卖双向,键盘快捷键(F1 买 / F2 卖 / Enter 提交)
- **撮合**:市价即时成交,限价单挂单等待价格触及;A 股真实成本(佣金万 2.5 / 印花税千 1 / 过户费)
- **风控**:单票仓位上限 / 总仓位上限 / 日内交易次数 / 持仓不足保护,下单前拦截
- **行情**:后端 APScheduler 定时拉取(交易时段内),SSE 推送 + 前端轮询双通道
- **K 线**:TradingView Lightweight Charts,MA5/MA20 叠加,成交量副图
- **信号源**:LSTM 预期收益 + LLM 报告作为决策参考(只读,不自动下单)
- **回测**:双均线策略,逐 bar 回放,输出净值曲线 / 夏普 / 最大回撤 / 胜率
- **正式预测**:收盘后自动生成 10 个交易日正式预测 + 沪深300完整排名,到期按交易日历自动结算复盘(只读旁路,不自动下单)

## 架构

```
┌─────────────────────────────────────────────┐
│  前端工作台 (React + AntD + TradingView)     │ :5173
│  三栏布局:自选 | K线+下单 | 信号+持仓       │
└────────────────┬────────────────────────────┘
                 │ HTTP + SSE
┌────────────────▼────────────────────────────┐
│  后端 API (FastAPI + Pydantic)               │ :8000
│  accounts / orders / market / signals / ...  │
├─────────────────────────────────────────────┤
│  服务层                                      │
│  AccountService / OrderService               │
│  MatchingEngine / RiskEngine / FeesCalc      │
├─────────────────────────────────────────────┤
│  数据层                                      │
│  SQLite + SQLAlchemy ORM                     │
│  APScheduler 行情调度                        │
│  旧 src/ 计算模块(technical/risk/predict)   │
└─────────────────────────────────────────────┘
```

## 快速开始

### 方式一:Docker 一键启动(推荐)

前置:本机已装 Docker 与 Docker Compose(`docker compose version` 能输出版本号即可)。

```bash
# 1. 准备环境变量(项目根已有 .env;没有则复制模板)
#    cp .env.example .env  # Linux/macOS
#    copy .env.example .env  # Windows

# 2. 构建并启动后端 + 前端工作台
docker compose up -d --build
```

启动后访问:

- **工作台**:http://localhost:5173
- **API 文档(Swagger)**:http://localhost:8000/docs

常用命令:

```bash
docker compose logs -f          # 跟踪日志
docker compose restart backend  # 重启后端
docker compose down             # 停止并清理容器
docker compose up -d --build    # 代码变更后重建
```

> 数据持久化:`./data` 目录通过卷挂载进容器,SQLite 与自选列表在宿主机保留,`docker compose down` 不会丢数据。

> 旧版 Streamlit 单页应用(`smart-trade.py`)默认不启动;需要时附带拉起:
> `docker compose --profile legacy up -d --build`,访问 http://localhost:8501。

### 方式二:本地开发(不用 Docker)

适合调试代码、热重载场景。需要 Python 3.12+ 与 Node 18+。

#### 1. 安装依赖

```powershell
# 后端
cd backend
pip install -r requirements.txt

# 前端
cd ..\frontend
npm install
```

国内网络建议加镜像源:

- pip:`-i https://pypi.tuna.tsinghua.edu.cn/simple`
- npm:`npm config set registry https://registry.npmmirror.com`

> **数据库迁移**:schema 由 Alembic 版本化管理(`backend/migrations/versions/`),应用启动时自动执行 `alembic upgrade head` 建表/升级,通常无需手动操作。手动命令:`cd backend; alembic upgrade head`(升级)、`alembic check`(校验 ORM 模型与迁移一致)。

#### 2. 配置

```powershell
cd backend
copy .env.example .env
# 按需编辑 .env:LLM_API_KEY(可选,信号源用)、DEBUG、费率等
```

#### 3. 启动

Windows:

```powershell
.\start_workbench.bat
```

macOS / Linux:

```bash
./start_workbench.sh
```

或分两个终端手动启动:

```powershell
# 终端 1:后端
cd backend; .\run.bat          # 或 bash run.sh

# 终端 2:前端
cd frontend; .\dev.bat
```

#### 4. 访问

- **工作台**:http://localhost:5173
- **API 文档(Swagger)**:http://localhost:8000/docs

### 端口与服务对照

| 服务 | 容器 | 端口 | 启动方式 |
|------|------|------|----------|
| 后端 API | `smart-stack-backend` | 8000 | 默认(Docker) / `backend/run.bat` |
| 前端工作台 | `smart-stack-frontend` | 5173 | 默认(Docker) / `frontend/dev.bat` |
| Streamlit 旧版 | `smart-stack-streamlit` | 8501 | `--profile legacy` / `streamlit run smart-trade.py` |

## 使用流程

1. 顶栏「新建」创建纸面账户(默认 100 万)
2. 左栏输入代码加自选(如 `000001`),点击选中
3. 中栏看 K 线,下方订单面板下单(限价 / 市价,买 / 卖)
4. 右栏查看 LSTM 信号、LLM 报告、当前持仓
5. 底部 Tab:委托中 / 成交记录 / 风控规则 / 回测

## 键盘快捷键

| 键 | 功能 |
|----|------|
| F1 | 切到买入 |
| F2 | 切到卖出 |
| Enter | 提交订单 |
| Esc | (组件内)取消 |

## 测试

```powershell
cd backend
$env:PYTHONPATH = "."
python -m pytest tests/ -v
```

覆盖:费用计算、撮合规则、风控拦截、持仓加权成本、订单全链路、回测引擎、交易日历、市场数据冻结与校验、预测引擎、筛选排名、到期结算,以及端到端验收(`test_forecast_pipeline_e2e.py`:冻结 → 筛选 → 预测 → 到期 → 结算)。完整阶段校验:`python -m pytest tests -q && alembic check`(后端)+ `cd ..\frontend && npm run build`(前端)。

## 目录结构

```
├─ backend/                 # FastAPI 后端
│  ├─ app/
│  │  ├─ api/               # 路由(accounts/orders/market/signals/...)
│  │  ├─ services/          # 业务编排(account/order/market/...)
│  │  ├─ engine/            # 纯计算(fees/matching/risk/technical)
│  │  ├─ models/            # SQLAlchemy ORM
│  │  ├─ schemas/           # Pydantic I/O
│  │  ├─ jobs/              # APScheduler 定时任务
│  │  └─ main.py            # FastAPI 入口
│  ├─ tests/                # pytest
│  └─ requirements.txt
├─ frontend/                # React 工作台
│  ├─ src/
│  │  ├─ components/        # 顶栏/自选/K线/订单/持仓/底部Tab
│  │  ├─ stores/            # Zustand 状态
│  │  ├─ api/               # axios 客户端
│  │  └─ types/             # TypeScript 类型
│  └─ package.json
├─ src/                     # 旧 Streamlit 分析模块(保留,作为 engine 源)
├─ smart-trade.py           # 旧 Streamlit 入口(legacy,见 README_legacy.md)
├─ data/                    # SQLite + 自选列表
└─ start_workbench.bat/.sh  # 一键启动
```

## 关键设计

- **服务端拉取行情**,而非前端轮询;交易时段判断按上交所日历(节假日表硬编码当年)
- **撮合引擎纯函数式**,输入(订单+行情)输出(成交),易测试
- **费用模型可配置**(`.env` 的 `FEES_*` 变量覆盖默认值)
- **风控下单前拦截**,任一规则不通过即 REJECTED + 原因码
- **信号源是只读旁路**,不自动触发下单,决策完全由人
- **旧分析模块复用**,`src/data` / `src/models` 的纯计算迁移到 `backend/app/engine/`

## 正式预测与研究管线

收盘后自动生成「正式预测」并对沪深300做完整排名,到期按交易日历自动结算复盘。整条管线是**只读旁路**:只生成预测、筛选与复盘结果,**绝不自动下单**。

### 每日研究调度

| 任务 | 时间(Asia/Shanghai) | 说明 |
|------|----------------------|------|
| 每日研究 `daily_research` | 交易日 16:30 | 冻结当日行情 → 对沪深300成分生成正式预测 → 完整排名 |
| 到期结算 `settlement` | 交易日 17:00 | 结算所有已到期预测,写入不可改写的复盘结果 |

时间可在 `MarketConfig` 调整(`daily_research_hour/minute`、`settlement_hour/minute`)。

### 预测契约

- **期限**:每条正式预测 horizon 固定为 **10 个交易日**(按交易日历而非自然日);到期日 = 业务日之后第 10 个交易日。
- **模型版本**:基准模型 `historical-10d-baseline @ 1.0.0`——确定性历史基准,相同输入产生相同输出,可复现、可回放。每条预测记录 `model_version_id`,前端展示模型名与版本。
- **字段**:概率分布(p_up / p_flat / p_down)、收益中位数与 10/90 分位区间、预期超额收益、预期 MFE / MAE。
- **结算**:到期后按第 1~10 个交易日计算实际收益、基准超额、符号误差、区间覆盖、MFE / MAE;缺少到期价格时置为 `PENDING_DATA`,不写零值。

### 筛选运行状态(部分筛选语义)

- `SUCCESS`:全部成分预测成功。
- `PARTIAL`:部分成功、部分失败——失败候选记录稳定原因码(如 `STALE_DATA` / `INSUFFICIENT_HISTORY` / `PREDICT_ERROR:*`),成功者照常排名。
- `FAILED`:无一成功。

完整排名与 Top10:`GET /api/screener/runs/{id}`;预测历史(最新在前):`GET /api/forecasts/{symbol}`。

### 本地手动扫描(不启用自动下单)

研究管线与下单完全隔离,手动触发只生成预测/筛选/结算,不会下任何订单(需可访问 AkShare 拉取行情):

```powershell
cd backend
python -c "from datetime import date; from app.db.base import SessionLocal; from app.services.market_service import MarketDataAdaptor; from app.services.screener_service import ScreeningPipeline; from app.jobs.daily_research import run_daily_research; print(run_daily_research(date(2026, 7, 21), SessionLocal, lambda s: ScreeningPipeline(s, MarketDataAdaptor())))"
```

把 `date(2026, 7, 21)` 换成目标业务日;传 `None` 则用当天。

## 不在本期范围

- 真实券商对接(架构预留,不实现)
- 期权 / 期货 / 融资融券(只做现货多头)
- 移动端适配(桌面优先)
- tick 级实时推送(60 秒轮询足够纸面操盘)

## 历史

旧版 Streamlit 单页分析应用见 [README_legacy.md](README_legacy.md),入口 `smart-trade.py` 仍可运行(`streamlit run smart-trade.py`)。

## License

MIT
