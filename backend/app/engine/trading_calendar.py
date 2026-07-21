"""交易日历引擎:基于 trading_calendar 表计算交易日偏移。

shift(start, n) 返回 start 之后第 n 个交易日(按交易日而非自然日计数)。
生产环境通过 ensure_loaded() 从 AkShare 拉取并缓存到 trading_calendar 表;
测试直接填充该表。
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.forecast import TradingCalendar as TradingCalendarRow


class TradingCalendar:
    def __init__(self, db: Session):
        self.db = db
        self._sessions: list[date] | None = None

    def _load(self) -> list[date]:
        if self._sessions is None:
            self._sessions = list(
                self.db.scalars(
                    select(TradingCalendarRow.session_date).order_by(
                        TradingCalendarRow.session_date
                    )
                ).all()
            )
        return self._sessions

    def ensure_loaded(
        self, start: date = date(2018, 1, 1), end: date = date(2026, 12, 31)
    ) -> None:
        """若表为空,从 AkShare 拉取历史交易日并缓存。"""
        if self._load():
            return
        import akshare as ak

        df = ak.tool_trade_date_hist_sina()
        col = df.columns[0]
        for value in df[col]:
            d = value if isinstance(value, date) else date.fromisoformat(str(value)[:10])
            if start <= d <= end:
                self.db.add(TradingCalendarRow(session_date=d))
        self.db.commit()
        self._sessions = None

    def shift(self, start: date, sessions: int) -> date:
        """返回 start 之后第 sessions 个交易日。"""
        future = [s for s in self._load() if s > start]
        if len(future) < sessions:
            raise ValueError("insufficient trading sessions in calendar")
        return future[sessions - 1]

    def sessions_after(self, start: date, sessions: int) -> list[date]:
        """返回 start 之后前 sessions 个交易日列表。"""
        future = [s for s in self._load() if s > start]
        return future[:sessions]

    def is_session(self, d: date) -> bool:
        return d in set(self._load())