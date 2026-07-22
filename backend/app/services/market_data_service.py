"""市场数据冻结服务:把校验通过的日线固化为不可改写的批次。

核心契约:
- freeze_daily_batch 对同一业务日幂等,重复调用返回同一 batch_id;
- 先写入指数成分快照,再逐 symbol 拉取/归一化/校验日线;
- 仅接受通过同一校验的数据,绝不在单个 symbol 序列内混用数据源;
- 每个被接受的归一化行写入不可改写的 DailyBar,并记录数据源、截止时间、
  行数、SHA-256 校验和、状态与逐 symbol 失败原因。
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.market_data_validation import (
    normalize_daily_bars,
    validate_daily_bars,
)
from app.models.forecast import DailyBar, MarketDataBatch, UniverseSnapshot

logger = logging.getLogger(__name__)

DEFAULT_INDEX_CODE = "000300"
LOOKBACK_DAYS = 300


@dataclass(frozen=True)
class UniverseMemberInput:
    """指数成分输入:股票代码 + 名称。"""

    symbol: str
    name: str = ""


@dataclass(frozen=True)
class FrozenMarketBatch:
    """一次冻结批次的对外结果。"""

    batch_id: str
    universe_snapshot_id: str
    valid_symbols: tuple[str, ...]
    failures: dict[str, str] = field(default_factory=dict)


class MarketDataService:
    """把校验通过的日线固化为不可改写的批次。"""

    def __init__(self, db: Session, adaptor):
        self.db = db
        self.adaptor = adaptor

    def freeze_daily_batch(
        self, business_date: date, members: list[UniverseMemberInput]
    ) -> FrozenMarketBatch:
        existing = self.db.scalars(
            select(MarketDataBatch).where(MarketDataBatch.business_date == business_date)
        ).first()
        if existing is not None:
            return self._to_frozen(existing)

        snapshot = self._store_universe_snapshot(business_date, members)

        valid_symbols: list[str] = []
        failures: dict[str, str] = {}
        accepted: list[tuple[str, pd.DataFrame]] = []
        primary_source = "none"
        cutoff: datetime | None = None

        for member in members:
            start = (business_date - timedelta(days=LOOKBACK_DAYS)).isoformat()
            end = business_date.isoformat()
            try:
                df, source = self.adaptor.load_kline(member.symbol, start, end)
            except Exception as exc:  # noqa: BLE001 记录任何数据源异常为失败原因
                failures[member.symbol] = f"SOURCE_ERROR:{exc}"
                continue

            norm = normalize_daily_bars(df)
            result = validate_daily_bars(norm, business_date)
            if result.valid:
                valid_symbols.append(member.symbol)
                accepted.append((member.symbol, norm))
                if cutoff is None:
                    primary_source = source or "unknown"
                    cutoff = datetime.now()
            else:
                failures[member.symbol] = result.reason or "INVALID"

        batch = MarketDataBatch(
            business_date=business_date,
            source=primary_source,
            cutoff_time=cutoff,
            status="SUCCESS" if valid_symbols else "FAILED",
            row_count=int(sum(len(norm) for _, norm in accepted)),
            checksum=self._checksum(accepted),
            failures_json=json.dumps(failures, ensure_ascii=False),
            universe_snapshot_id=snapshot.id,
        )
        self.db.add(batch)
        self.db.flush()

        for symbol, norm in accepted:
            for row in norm.itertuples(index=False):
                self.db.add(
                    DailyBar(
                        market_data_batch_id=batch.id,
                        symbol=symbol,
                        date=row.date,
                        open=float(row.open),
                        high=float(row.high),
                        low=float(row.low),
                        close=float(row.close),
                        volume=float(row.volume),
                        adj_factor=float(row.adj_factor),
                    )
                )
        self.db.commit()

        return FrozenMarketBatch(
            batch_id=batch.id,
            universe_snapshot_id=snapshot.id,
            valid_symbols=tuple(valid_symbols),
            failures=failures,
        )

    def _store_universe_snapshot(
        self, business_date: date, members: list[UniverseMemberInput]
    ) -> UniverseSnapshot:
        existing = self.db.scalars(
            select(UniverseSnapshot).where(
                UniverseSnapshot.business_date == business_date,
                UniverseSnapshot.index_code == DEFAULT_INDEX_CODE,
            )
        ).first()
        if existing is not None:
            return existing

        members_json = json.dumps(
            [{"symbol": m.symbol, "name": m.name} for m in members],
            ensure_ascii=False,
        )
        snapshot = UniverseSnapshot(
            business_date=business_date,
            index_code=DEFAULT_INDEX_CODE,
            members_json=members_json,
        )
        self.db.add(snapshot)
        self.db.flush()
        return snapshot

    def _to_frozen(self, batch: MarketDataBatch) -> FrozenMarketBatch:
        symbols = self.db.scalars(
            select(DailyBar.symbol)
            .where(DailyBar.market_data_batch_id == batch.id)
            .distinct()
        ).all()
        failures = json.loads(batch.failures_json) if batch.failures_json else {}
        return FrozenMarketBatch(
            batch_id=batch.id,
            universe_snapshot_id=batch.universe_snapshot_id or "",
            valid_symbols=tuple(sorted(symbols)),
            failures=failures,
        )

    @staticmethod
    def _checksum(accepted: list[tuple[str, pd.DataFrame]]) -> str:
        """对有效日线内容计算稳定的 SHA-256 校验和。"""
        digest = hashlib.sha256()
        for symbol, norm in sorted(accepted, key=lambda item: item[0]):
            for row in norm.itertuples(index=False):
                line = (
                    f"{symbol}|{row.date}|{row.open}|{row.high}|{row.low}|"
                    f"{row.close}|{row.volume}|{row.adj_factor}\n"
                )
                digest.update(line.encode("utf-8"))
        return digest.hexdigest()