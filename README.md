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

### 1. 安装依赖

```powershell
# 后端(Python 3.12+)
cd backend
pip install -r requirements.txt

# 前端(Node 18+)
cd ..\frontend
npm install
```

国内网络建议加镜像:
- pip: `-i https://pypi.tuna.tsinghua.edu.cn/simple`
- npm: `npm config set registry https://registry.npmmirror.com`

### 2. 配置

```powershell
cd backend
copy .env.example .env
# 按需编辑 .env:LLM_API_KEY(可选,信号源用)、DEBUG、费率等
```

### 3. 一键启动

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

### 4. 访问

- **工作台**:http://localhost:5173
- **API 文档(Swagger)**:http://localhost:8000/docs

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

覆盖:费用计算、撮合规则、风控拦截、持仓加权成本、订单全链路、回测引擎。

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

## 不在本期范围

- 真实券商对接(架构预留,不实现)
- 期权 / 期货 / 融资融券(只做现货多头)
- 移动端适配(桌面优先)
- tick 级实时推送(60 秒轮询足够纸面操盘)

## 历史

旧版 Streamlit 单页分析应用见 [README_legacy.md](README_legacy.md),入口 `smart-trade.py` 仍可运行(`streamlit run smart-trade.py`)。

## License

MIT
