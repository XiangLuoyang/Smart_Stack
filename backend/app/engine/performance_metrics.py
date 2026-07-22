"""透明性能指标计算(纯函数)。

所有函数返回 dataclass(value + sample_count),缺失数据仅从对应指标中剔除,不填零。
方向判定使用 +/-1% 平坦带。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np


FLAT_BAND = 0.01


@dataclass(frozen=True)
class MetricResult:
    value: Optional[float]
    sample_count: int


def _direction_label(r: float) -> int:
    if r > FLAT_BAND:
        return 1
    if r < -FLAT_BAND:
        return -1
    return 0


def direction_accuracy(
    predicted: Sequence[float], actual: Sequence[float]
) -> MetricResult:
    pairs = [(p, a) for p, a in zip(predicted, actual) if p is not None and a is not None]
    if not pairs:
        return MetricResult(None, 0)
    correct = sum(1 for p, a in pairs if _direction_label(p) == _direction_label(a))
    return MetricResult(correct / len(pairs), len(pairs))


def mae(predicted: Sequence[float], actual: Sequence[float]) -> MetricResult:
    pairs = [(p, a) for p, a in zip(predicted, actual) if p is not None and a is not None]
    if not pairs:
        return MetricResult(None, 0)
    errors = [abs(p - a) for p, a in pairs]
    return MetricResult(float(np.mean(errors)), len(pairs))


def rmse(predicted: Sequence[float], actual: Sequence[float]) -> MetricResult:
    pairs = [(p, a) for p, a in zip(predicted, actual) if p is not None and a is not None]
    if not pairs:
        return MetricResult(None, 0)
    errors = [(p - a) ** 2 for p, a in pairs]
    return MetricResult(float(np.sqrt(np.mean(errors))), len(pairs))


def interval_coverage(
    actual: Sequence[float],
    lower: Sequence[float],
    upper: Sequence[float],
) -> MetricResult:
    triples = [
        (a, lo, hi)
        for a, lo, hi in zip(actual, lower, upper)
        if a is not None and lo is not None and hi is not None
    ]
    if not triples:
        return MetricResult(None, 0)
    covered = sum(1 for a, lo, hi in triples if lo <= a <= hi)
    return MetricResult(covered / len(triples), len(triples))


def spearman_rank(
    ranks: Sequence[float], returns: Sequence[float]
) -> MetricResult:
    pairs = [(r, ret) for r, ret in zip(ranks, returns) if r is not None and ret is not None]
    if len(pairs) < 5:
        return MetricResult(None, len(pairs))
    r_arr = np.array([p[0] for p in pairs])
    ret_arr = np.array([p[1] for p in pairs])
    if np.std(r_arr) == 0 or np.std(ret_arr) == 0:
        return MetricResult(None, len(pairs))
    from scipy.stats import spearmanr
    corr, _ = spearmanr(r_arr, ret_arr)
    return MetricResult(float(corr), len(pairs))


def top_n_return(
    ranks: Sequence[int],
    actual: Sequence[float],
    top_n: int = 10,
) -> MetricResult:
    pairs = [(r, a) for r, a in zip(ranks, actual) if r is not None and a is not None and r <= top_n]
    if not pairs:
        return MetricResult(None, 0)
    returns = [a for _, a in pairs]
    return MetricResult(float(np.mean(returns)), len(pairs))


def top_n_excess_return(
    ranks: Sequence[int],
    actual: Sequence[float],
    benchmark_return: float,
    top_n: int = 10,
) -> MetricResult:
    result = top_n_return(ranks, actual, top_n)
    if result.value is None:
        return MetricResult(None, 0)
    return MetricResult(result.value - benchmark_return, result.sample_count)


def model_metrics(
    pred: Sequence[float],
    actual: Sequence[float],
    lower: Sequence[float],
    upper: Sequence[float],
) -> dict:
    return {
        "direction_accuracy": direction_accuracy(pred, actual),
        "mae": mae(pred, actual),
        "rmse": rmse(pred, actual),
        "interval_coverage": interval_coverage(actual, lower, upper),
    }


def ranking_metrics(
    ranks: Sequence[int],
    actual: Sequence[float],
    benchmark: float,
    top_n: int = 10,
) -> dict:
    return {
        "top_n_return": top_n_return(ranks, actual, top_n),
        "top_n_excess_return": top_n_excess_return(ranks, actual, benchmark, top_n),
    }

def execution_increment(
    decision_return: Sequence[float],
    actual_execution_return: Sequence[float],
) -> MetricResult:
    """执行增量:实际执行收益 vs 决策时预期收益的差值。

    正值表示执行优于决策(好的时机/价格),负值表示执行损耗。
    """
    pairs = [
        (d, e)
        for d, e in zip(decision_return, actual_execution_return)
        if d is not None and e is not None
    ]
    if not pairs:
        return MetricResult(None, 0)
    increments = [e - d for d, e in pairs]
    return MetricResult(float(np.mean(increments)), len(pairs))