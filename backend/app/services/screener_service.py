"""沪深300筛选服务:数据库驱动的完整排名运行。

取代旧的内存/JSON 单例选股。每次运行冻结一批行情、对每个有效成分生成
正式预测,按 expected_excess_return DESC / median_return DESC / symbol ASC
排名,持久化全部成功与失败候选;以 (business_date, model_version_id) 幂等。
"""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.models.forecast import (
    MarketDataBatch,
    ModelVersion,
    ScreeningCandidate,
    ScreeningRun,
)
from app.services.forecast_service import ForecastService, register_baseline_model
from app.services.market_data_service import (
    DEFAULT_INDEX_CODE,
    MarketDataService,
    UniverseMemberInput,
)

logger = logging.getLogger(__name__)


class ScreeningPipeline:
    """生产用筛选管线:冻结行情 + 生成正式预测。

    members_provider 可注入以便测试/回放;默认从 akshare 拉取沪深300成分,
    并附加基准指数代码,使基准日线一并被冻结供超额收益计算。
    """

    def __init__(self, db: Session, adaptor, members_provider=None):
        self.db = db
        self.adaptor = adaptor
        self._members_provider = members_provider or self._default_members

    def _default_members(self, business_date: date) -> list[UniverseMemberInput]:
        import akshare as ak

        df = ak.index_stock_cons_csindex(symbol=DEFAULT_INDEX_CODE)
        cols = list(df.columns)
        code_col = next((c for c in cols if "代码" in str(c)), cols[0])
        name_col = next((c for c in cols if "名称" in str(c)), cols[1])
        members: list[UniverseMemberInput] = []
        for _, row in df.iterrows():
            code = str(row.get(code_col, "")).strip()
            name = str(row.get(name_col, "")).strip()
            if code:
                members.append(UniverseMemberInput(code, name))
        members.append(UniverseMemberInput(DEFAULT_INDEX_CODE, "沪深300"))
        return members

    def freeze(self, business_date: date):
        members = self._members_provider(business_date)
        return MarketDataService(self.db, self.adaptor).freeze_daily_batch(
            business_date, members
        )

    def predict(self, frozen, model_version_id: str, symbol: str):
        model = self.db.get(ModelVersion, model_version_id)
        if model is None:
            model = register_baseline_model(self.db)
        return ForecastService(self.db).create_formal_prediction(frozen, model, symbol)


class ScreenerService:
    """数据库驱动的筛选运行。pipeline 仅在 run() 时需要,读取操作可省略。"""

    def __init__(self, db: Session, pipeline=None):
        self.db = db
        self.pipeline = pipeline

    def run(self, business_date: date, model_version_id: str) -> ScreeningRun:
        if self.pipeline is None:
            raise ValueError("a screening pipeline is required to run a screen")

        existing = self.db.scalars(
            select(ScreeningRun).where(
                ScreeningRun.business_date == business_date,
                ScreeningRun.model_version_id == model_version_id,
            )
        ).first()
        if existing is not None:
            return existing

        frozen = self.pipeline.freeze(business_date)
        failures: dict[str, str] = dict(frozen.failures)
        candidate_symbols = [s for s in frozen.valid_symbols if s != DEFAULT_INDEX_CODE]

        successes: list[tuple[str, object]] = []
        for symbol in candidate_symbols:
            try:
                prediction = self.pipeline.predict(frozen, model_version_id, symbol)
                successes.append((symbol, prediction))
            except Exception as exc:  # noqa: BLE001 预测失败记为失败候选
                failures[symbol] = f"PREDICT_ERROR:{exc}"

        successes.sort(
            key=lambda item: (
                -item[1].expected_excess_return,
                -item[1].median_return,
                item[0],
            )
        )

        success_count = len(successes)
        failure_count = len(failures)
        if success_count == 0:
            run_status = "FAILED"
        elif failure_count == 0:
            run_status = "SUCCESS"
        else:
            run_status = "PARTIAL"

        run = ScreeningRun(
            business_date=business_date,
            model_version_id=model_version_id,
            market_data_batch_id=frozen.batch_id,
            status=run_status,
            success_count=success_count,
            failure_count=failure_count,
            failure_reason=None,
        )
        self.db.add(run)
        self.db.flush()

        for rank, (symbol, prediction) in enumerate(successes, start=1):
            self.db.add(
                ScreeningCandidate(
                    screening_run_id=run.id,
                    symbol=symbol,
                    rank=rank,
                    score=float(prediction.expected_excess_return),
                    prediction_snapshot_id=prediction.id,
                    status="SUCCESS",
                    failure_reason=None,
                )
            )
        for symbol, reason in failures.items():
            self.db.add(
                ScreeningCandidate(
                    screening_run_id=run.id,
                    symbol=symbol,
                    rank=0,
                    score=0.0,
                    prediction_snapshot_id=None,
                    status="FAILED",
                    failure_reason=reason,
                )
            )
        self.db.commit()
        return run

    def list_candidates(self, run_id: str) -> list[ScreeningCandidate]:
        status_order = case(
            (ScreeningCandidate.status == "SUCCESS", 0), else_=1
        )
        return list(
            self.db.scalars(
                select(ScreeningCandidate)
                .where(ScreeningCandidate.screening_run_id == run_id)
                .order_by(
                    status_order,
                    ScreeningCandidate.rank.asc(),
                    ScreeningCandidate.symbol.asc(),
                )
            ).all()
        )

    def list_runs(self, limit: int = 20, offset: int = 0) -> list[ScreeningRun]:
        return list(
            self.db.scalars(
                select(ScreeningRun)
                .order_by(ScreeningRun.business_date.desc())
                .limit(limit)
                .offset(offset)
            ).all()
        )

    def get_run(self, run_id: str) -> ScreeningRun | None:
        return self.db.get(ScreeningRun, run_id)