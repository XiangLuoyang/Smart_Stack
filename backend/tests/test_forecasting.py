"""确定性预测引擎契约测试。"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from app.engine.forecasting import ForecastEngine


def _price_series(n, base, seed):
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0, 0.01, n)
    return base * np.cumprod(1.0 + steps)


def _frame(prices, as_of):
    n = len(prices)
    dates = [as_of - timedelta(days=i) for i in range(n - 1, -1, -1)]
    return pd.DataFrame({"date": dates, "close": prices, "adj_factor": 1.0})


@pytest.fixture
def price_frame():
    return _frame(_price_series(130, 10.0, seed=1), date(2026, 7, 21))


@pytest.fixture
def benchmark_frame():
    return _frame(_price_series(130, 4000.0, seed=2), date(2026, 7, 21))


def test_baseline_forecast_contract(price_frame, benchmark_frame):
    out = ForecastEngine().predict(price_frame, benchmark_frame)
    assert out.horizon_days == 10
    assert abs(out.p_up + out.p_flat + out.p_down - 1.0) < 1e-9
    assert out.lower_return <= out.median_return <= out.upper_return


def test_forecast_is_deterministic(price_frame, benchmark_frame):
    first = ForecastEngine().predict(price_frame, benchmark_frame)
    second = ForecastEngine().predict(price_frame, benchmark_frame)
    assert first == second


def test_forecast_rejects_insufficient_history(benchmark_frame):
    short = benchmark_frame.head(5)
    with pytest.raises(ValueError):
        ForecastEngine().predict(short, benchmark_frame)