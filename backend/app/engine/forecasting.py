"""确定性 10 日预测引擎(历史基准模型)。

纯函数式引擎:输入股票与基准的复权日线,输出统一期限(10 个交易日)的
概率分布、收益区间与超额收益。不使用未来数据,不依赖随机性,相同输入
产生相同输出,便于复现与回放。

方法:以复权收盘价构造历史 10 日前向收益,等权取最近 60 个观测;
abs(return) <= 0.01 视为持平;区间取经验 10/50/90 分位;超额收益为
个股中位数减去基准中位数。MFE/MAE 取持有窗口内的最大有利/不利 excursion。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

HORIZON_DAYS = 10
WINDOW_OBSERVATIONS = 60
FLAT_THRESHOLD = 0.01


@dataclass(frozen=True)
class ForecastOutput:
    horizon_days: int
    p_up: float
    p_flat: float
    p_down: float
    median_return: float
    lower_return: float
    upper_return: float
    expected_excess_return: float
    expected_mfe: float
    expected_mae: float


class ForecastEngine:
    """历史基准预测引擎。"""

    def __init__(self, horizon_days: int = HORIZON_DAYS):
        self.horizon_days = horizon_days

    def predict(self, frame: pd.DataFrame, benchmark: pd.DataFrame) -> ForecastOutput:
        adj = self._adjusted_close_series(frame)
        forward, mfe, mae = self._forward_stats(adj)
        if len(forward) == 0:
            raise ValueError("insufficient history to build forward returns")

        forward = forward[-WINDOW_OBSERVATIONS:]
        mfe = mfe[-WINDOW_OBSERVATIONS:]
        mae = mae[-WINDOW_OBSERVATIONS:]

        p_up = float(np.mean(forward > FLAT_THRESHOLD))
        p_flat = float(np.mean(np.abs(forward) <= FLAT_THRESHOLD))
        p_down = float(np.mean(forward < -FLAT_THRESHOLD))

        median_return = float(np.percentile(forward, 50))
        lower_return = float(np.percentile(forward, 10))
        upper_return = float(np.percentile(forward, 90))
        expected_mfe = float(np.mean(mfe))
        expected_mae = float(np.mean(mae))

        bench_adj = self._adjusted_close_series(benchmark)
        bench_forward, _, _ = self._forward_stats(bench_adj)
        bench_median = (
            float(np.percentile(bench_forward[-WINDOW_OBSERVATIONS:], 50))
            if len(bench_forward)
            else 0.0
        )
        expected_excess_return = median_return - bench_median

        return ForecastOutput(
            horizon_days=self.horizon_days,
            p_up=p_up,
            p_flat=p_flat,
            p_down=p_down,
            median_return=median_return,
            lower_return=lower_return,
            upper_return=upper_return,
            expected_excess_return=expected_excess_return,
            expected_mfe=expected_mfe,
            expected_mae=expected_mae,
        )

    def _adjusted_close_series(self, frame: pd.DataFrame) -> np.ndarray:
        df = frame.copy()
        if "adj_factor" not in df.columns:
            df["adj_factor"] = 1.0
        df["adj_close"] = df["close"].astype(float) * df["adj_factor"].astype(float)
        df = df.sort_values("date")
        return df["adj_close"].to_numpy(dtype=float)

    def _forward_stats(self, adj_close: np.ndarray):
        """返回每个入场日的 (10日前向收益, MFE, MAE) 数组。"""
        n = len(adj_close)
        h = self.horizon_days
        forward_returns: list[float] = []
        mfes: list[float] = []
        maes: list[float] = []
        for t in range(n - h):
            entry = adj_close[t]
            if entry <= 0:
                continue
            window = adj_close[t + 1 : t + 1 + h]
            if len(window) < h:
                continue
            path_returns = window / entry - 1.0
            forward_returns.append(float(path_returns[-1]))
            mfes.append(float(path_returns.max()))
            maes.append(float(path_returns.min()))
        return (
            np.array(forward_returns, dtype=float),
            np.array(mfes, dtype=float),
            np.array(maes, dtype=float),
        )