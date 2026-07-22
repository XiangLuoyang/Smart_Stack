"""到期预测结算服务:基于交易日历计算实际表现,写入不可改写的复盘结果。

核心契约:
- 仅结算已到期(maturity <= as_of)且尚未结算的预测;
- 实际收益/基准超额/符号误差/区间覆盖/MFE/MAE 均按第 1 至第 10 个交易日计算;
- ReviewResult 以 prediction_snapshot_id 唯一;已结算则原样返回,不重复写入;
- 缺少到期价格时将预测置为 PENDING_DATA,不写入零值结果。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.trading_calendar import TradingCalendar
from app.models.forecast import DailyBar, PredictionSnapshot, ReviewResult
from app.services.market_data_service import DEFAULT_INDEX_CODE

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SettlementSummary:
    settled: int
    pending_data: int
    as_of: date


class BarSource:
    """复权收盘价数据源协议。"""

    def adjusted_close(self, symbol: str, on_date: date) -> float | None:
        raise NotImplementedError


class DatabaseBarSource(BarSource):
    """从已冻结的 DailyBar 读取复权收盘价(close * adj_factor)。"""

    def __init__(self, db: Session):
        self.db = db

    def adjusted_close(self, symbol: str, on_date: date) -> float | None:
        bar = self.db.scalars(
            select(DailyBar).where(DailyBar.symbol == symbol, DailyBar.date == on_date)
        ).first()
        return bar.close * bar.adj_factor if bar else None


class ReviewService:
    def __init__(self, db: Session, bars: BarSource):
        self.db = db
        self.bars = bars
        self.calendar = TradingCalendar(db)

    def settle_due(self, as_of: date) -> SettlementSummary:
        predictions = self.db.scalars(
            select(PredictionSnapshot).where(
                PredictionSnapshot.state.in_(["PENDING", "PENDING_DATA"])
            )
        ).all()

        settled = 0
        pending_data = 0
        for pred in predictions:
            existing = self.db.scalars(
                select(ReviewResult).where(
                    ReviewResult.prediction_snapshot_id == pred.id
                )
            ).first()
            if existing is not None:
                continue
            try:
                maturity = self.calendar.shift(pred.business_date, pred.horizon_days)
            except ValueError:
                continue
            if maturity > as_of:
                continue

            review = self._settle_one(pred, maturity)
            if review is None:
                pred.state = "PENDING_DATA"
                pending_data += 1
            else:
                settled += 1

        self.db.commit()
        return SettlementSummary(settled=settled, pending_data=pending_data, as_of=as_of)

    def _settle_one(self, pred: PredictionSnapshot, maturity: date) -> ReviewResult | None:
        entry = self.bars.adjusted_close(pred.symbol, pred.business_date)
        maturity_price = self.bars.adjusted_close(pred.symbol, maturity)
        if entry is None or maturity_price is None or entry <= 0:
            return None

        actual_return = maturity_price / entry - 1.0

        path_dates = self.calendar.sessions_after(pred.business_date, pred.horizon_days)
        path_returns: list[float] = []
        for d in path_dates:
            close = self.bars.adjusted_close(pred.symbol, d)
            if close is not None and entry > 0:
                path_returns.append(close / entry - 1.0)
        mfe = max(path_returns) if path_returns else actual_return
        mae = min(path_returns) if path_returns else actual_return

        bench_entry = self.bars.adjusted_close(DEFAULT_INDEX_CODE, pred.business_date)
        bench_maturity = self.bars.adjusted_close(DEFAULT_INDEX_CODE, maturity)
        benchmark_excess = None
        if bench_entry and bench_maturity and bench_entry > 0:
            benchmark_excess = actual_return - (bench_maturity / bench_entry - 1.0)

        signed_error = actual_return - pred.median_return
        interval_coverage = bool(pred.lower_return <= actual_return <= pred.upper_return)
        direction_correct = bool((actual_return > 0) == (pred.median_return > 0))

        review = ReviewResult(
            prediction_snapshot_id=pred.id,
            actual_return=actual_return,
            benchmark_excess=benchmark_excess,
            signed_error=signed_error,
            interval_coverage=interval_coverage,
            mfe=mfe,
            mae=mae,
            direction_correct=direction_correct,
            state="SETTLED",
            settled_at=datetime.now(),
        )
        self.db.add(review)
        pred.state = "SETTLED"
        return review