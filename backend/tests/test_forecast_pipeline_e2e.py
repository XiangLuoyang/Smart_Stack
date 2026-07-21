"""阶段一端到端验收:冻结 -> 筛选 -> 预测 -> 到期 -> 结算。

用一个确定性行情适配器驱动真实管线(真实冻结、真实预测引擎、真实结算),
证明同一输入产生同一输出、正式预测为 10 个交易日契约、到期后按交易日历结算,
且到期前不会提前结算。
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest
from sqlalchemy import select

from app.models.forecast import PredictionSnapshot
from app.services.forecast_service import register_baseline_model
from app.services.market_data_service import UniverseMemberInput
from app.services.screener_service import ScreenerService, ScreeningPipeline

BUSINESS_DATE = date(2026, 7, 21)
MATURITY_DATE = date(2026, 8, 4)  # 2026-07-21 之后第 10 个交易日
STOCKS = ["000001", "600000", "600036"]
BENCHMARK = "000300"

_BASE_PRICE = {"000001": 10.0, "600000": 8.0, "600036": 30.0, "000300": 4000.0}


class DeterministicAdaptor:
    """确定性行情源:价格为日期的纯函数,相同 (symbol, date) 永远返回相同值。

    load_kline 返回截至 end 的最近 130 个工作日日线(>= MIN_HISTORY_ROWS),
    最后一根恰为 end,满足冻结校验(无未来数据 / 非陈旧 / 历史充足)。
    """

    def _price(self, symbol: str, d: date) -> float:
        base = _BASE_PRICE[symbol]
        drift = (d.toordinal() - date(2026, 1, 1).toordinal()) * 0.0008
        osc = ((d.toordinal() % 5) - 2) * 0.006
        return round(base * (1 + drift + osc), 4)

    def load_kline(self, symbol, start, end):
        end_d = date.fromisoformat(end)
        dates: list[date] = []
        cur = end_d
        while len(dates) < 130:
            if cur.weekday() < 5:
                dates.append(cur)
            cur -= timedelta(days=1)
        rows = []
        for d in sorted(dates):
            p = self._price(symbol, d)
            rows.append(
                {
                    "date": d,
                    "open": p,
                    "high": p,
                    "low": p,
                    "close": p,
                    "volume": 1_000_000.0,
                    "adj_factor": 1.0,
                }
            )
        return pd.DataFrame(rows), "deterministic"


@pytest.fixture
def members():
    """3 只成分股 + 基准指数(基准用于超额收益,不参与排名)。"""
    return [UniverseMemberInput(s, s) for s in STOCKS] + [
        UniverseMemberInput(BENCHMARK, "沪深300")
    ]


def test_forecast_pipeline_e2e(client, db_session, trading_calendar_populated, members):
    # --- 冻结 + 筛选 + 预测(真实管线、真实预测引擎)---
    adaptor = DeterministicAdaptor()
    pipeline = ScreeningPipeline(
        db_session, adaptor, members_provider=lambda bd: members
    )
    model = register_baseline_model(db_session)
    run = ScreenerService(db_session, pipeline).run(BUSINESS_DATE, model.id)

    assert run.status == "SUCCESS"
    assert run.success_count == 3
    assert run.failure_count == 0

    preds = list(
        db_session.scalars(
            select(PredictionSnapshot).where(
                PredictionSnapshot.business_date == BUSINESS_DATE
            )
        ).all()
    )
    assert len(preds) == 3
    assert all(p.horizon_days == 10 for p in preds)
    assert all(p.state == "PENDING" for p in preds)

    # --- 到期:冻结覆盖前向路径的行情(模拟后续每日冻结累积日线)---
    pipeline.freeze(MATURITY_DATE)

    # 到期前不应结算(按交易日历 gating)
    pre = client.post("/api/reviews/settle", json={"as_of": "2026-07-22"})
    assert pre.status_code == 200
    assert pre.json()["settled"] == 0

    # --- 结算(经由 HTTP 端点,真实 ReviewService + DatabaseBarSource)---
    resp = client.post("/api/reviews/settle", json={"as_of": "2026-08-04"})
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["settled"] == 3
    assert summary["pending_data"] == 0

    # --- 预测历史端点反映已结算状态,且为 10 日契约 ---
    hist = client.get("/api/forecasts/000001").json()
    assert hist[0]["business_date"] == "2026-07-21"
    assert hist[0]["horizon_days"] == 10
    assert hist[0]["state"] == "SETTLED"