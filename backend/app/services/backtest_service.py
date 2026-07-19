"""回测服务:历史 K 线逐 bar 回放,复用撮合 + 费用逻辑。

策略接口(本期实现一个最简单的示例:双均线策略)。
输出:净值曲线、夏普、最大回撤、胜率。
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

import numpy as np
import pandas as pd
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.engine.fees import FeesCalculator
from app.models.backtest import BacktestRun, BacktestTrade

logger = logging.getLogger(__name__)


@dataclass
class BacktestState:
    """回测运行时账户状态。"""

    cash: float = 1_000_000.0
    position_qty: float = 0.0
    position_cost: float = 0.0  # 加权平均成本
    trades: list[dict] = field(default_factory=list)
    equity_curve: list[dict] = field(default_factory=list)

    @property
    def position_value(self) -> float:
        return self.position_qty * self.position_cost


def strategy_ma_cross(df: pd.DataFrame, params: dict) -> pd.Series:
    """双均线策略:MA_fast 上穿 MA_buy → 1(买),下穿 → -1(卖)。"""
    fast = params.get("fast", 5)
    slow = params.get("slow", 20)
    ma_fast = df["Close"].rolling(fast).mean()
    ma_slow = df["Close"].rolling(slow).mean()
    signal = pd.Series(0, index=df.index)
    signal[ma_fast > ma_slow] = 1
    signal[ma_fast <= ma_slow] = -1
    return signal


STRATEGIES: dict[str, Callable[[pd.DataFrame, dict], pd.Series]] = {
    "ma_cross": strategy_ma_cross,
}


def _metrics_from_curve(curve: list[dict], trades: list[dict]) -> dict:
    """从净值曲线算关键指标。"""
    if not curve:
        return {
            "total_return": 0.0, "sharpe": 0.0,
            "max_drawdown": 0.0, "win_rate": 0.0, "trade_count": 0,
        }
    nvs = np.array([p["nv"] for p in curve])
    total_return = float(nvs[-1] / nvs[0] - 1) if nvs[0] > 0 else 0.0
    rets = np.diff(nvs) / nvs[:-1]
    sharpe = 0.0
    if rets.std() > 0:
        sharpe = float(rets.mean() / rets.std() * np.sqrt(252))
    running_max = np.maximum.accumulate(nvs)
    dd = (nvs - running_max) / running_max
    max_dd = float(abs(dd.min())) if len(dd) > 0 else 0.0
    win = sum(1 for t in trades if t.get("pnl", 0) > 0)
    win_rate = win / len(trades) if trades else 0.0
    return {
        "total_return": round(total_return, 4),
        "sharpe": round(sharpe, 4),
        "max_drawdown": round(max_dd, 4),
        "win_rate": round(win_rate, 4),
        "trade_count": len(trades),
    }


class BacktestService:
    def __init__(self, db: Session, fees: FeesCalculator | None = None):
        self.db = db
        self.fees = fees or FeesCalculator()

    def run(
        self,
        symbol: str,
        strategy_name: str,
        params: dict,
        df: pd.DataFrame,
        start: datetime,
        end: datetime,
        initial_cash: float = 1_000_000.0,
    ) -> BacktestRun:
        if strategy_name not in STRATEGIES:
            raise ValueError(f"未知策略 {strategy_name},可选 {list(STRATEGIES)}")
        if df.empty:
            raise ValueError("回测数据为空")

        strategy = STRATEGIES[strategy_name]
        signals = strategy(df, params)
        state = BacktestState(cash=initial_cash)
        prev_signal = 0

        for i, row in df.iterrows():
            price = float(row["Close"])
            ts = pd.to_datetime(row.get("Date", datetime.now())).to_pydatetime()
            if ts < start or ts > end:
                continue

            sig = int(signals.iloc[i]) if i < len(signals) else 0

            if sig == 1 and prev_signal != 1 and state.position_qty == 0:
                qty = state.cash * 0.95 / price
                delta = self.fees.cash_delta("BUY", symbol, price, qty)  # 负数
                if -delta <= state.cash:
                    state.position_qty += qty
                    state.position_cost = price
                    state.cash += delta
                    state.trades.append({"ts": ts.isoformat(), "side": "BUY", "qty": qty, "price": price})
            elif sig == -1 and state.position_qty > 0:
                qty = state.position_qty
                delta = self.fees.cash_delta("SELL", symbol, price, qty)  # 正数
                pnl = delta - qty * state.position_cost
                state.cash += delta
                state.trades.append({
                    "ts": ts.isoformat(), "side": "SELL", "qty": qty, "price": price, "pnl": pnl
                })
                state.position_qty = 0.0
                state.position_cost = 0.0
            prev_signal = sig

            nv = (state.cash + state.position_qty * price) / initial_cash
            state.equity_curve.append({"ts": ts.isoformat(), "nv": round(nv, 6)})

        metrics = _metrics_from_curve(state.equity_curve, state.trades)
        run = BacktestRun(
            strategy_name=strategy_name,
            params_json=json.dumps({"symbol": symbol, **params}, ensure_ascii=False),
            start=start,
            end=end,
            metrics_json=json.dumps(metrics, ensure_ascii=False),
            equity_curve_json=json.dumps(state.equity_curve, ensure_ascii=False),
        )
        self.db.add(run)
        self.db.flush()
        for t in state.trades:
            self.db.add(BacktestTrade(
                run_id=run.id, symbol=symbol, side=t["side"],
                qty=t["qty"], price=t["price"],
                ts=datetime.fromisoformat(t["ts"]),
            ))
        self.db.commit()
        self.db.refresh(run)
        return run

    def get(self, run_id: str) -> BacktestRun | None:
        return self.db.get(BacktestRun, run_id)

    def list_runs(self, limit: int = 50) -> list[BacktestRun]:
        stmt = select(BacktestRun).order_by(desc(BacktestRun.created_at)).limit(limit)
        return list(self.db.scalars(stmt))
