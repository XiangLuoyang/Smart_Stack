"""市场数据冻结与校验测试。"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from app.engine.market_data_validation import normalize_daily_bars, validate_daily_bars
from app.models.forecast import DailyBar, MarketDataBatch
from app.services.market_data_service import (
    MarketDataService,
    UniverseMemberInput,
)


def frame(rows):
    """由 (date, close) 元组构造标准日线 DataFrame(open=high=low=close)。"""
    records = []
    for item in rows:
        d, close = item
        if isinstance(d, str):
            d = date.fromisoformat(d)
        records.append(
            {
                "date": d,
                "open": close,
                "high": close,
                "low": close,
                "close": close,
                "volume": 1000.0,
                "adj_factor": 1.0,
            }
        )
    return pd.DataFrame(records)


def make_bars(as_of, n=130, close=10.0):
    """构造以 as_of 结尾、共 n 行的有效日线。"""
    dates = [as_of - timedelta(days=i) for i in range(n - 1, -1, -1)]
    return frame([(d, close) for d in dates])


MEMBERS = [
    UniverseMemberInput("000001", "平安银行"),
    UniverseMemberInput("600000", "浦发银行"),
]


class FakeSource:
    """可控行情数据源:按 symbol 返回预设日线。"""

    def __init__(self, data):
        self._data = data
        self.calls: list[str] = []

    def load_kline(self, symbol, start_date=None, end_date=None):
        self.calls.append(symbol)
        if symbol in self._data:
            return self._data[symbol]
        return pd.DataFrame(), "none"


@pytest.fixture
def fake_source():
    as_of = date(2026, 7, 21)
    return FakeSource(
        {
            "000001": (make_bars(as_of, 130, 10.0), "fake"),
            "600000": (make_bars(as_of, 130, 20.0), "fake"),
        }
    )


# ---------------- 校验 ----------------


def test_rejects_future_bar():
    df = frame([("2026-07-21", 10.0), ("2026-07-22", 11.0)])
    result = validate_daily_bars(df, date(2026, 7, 21))
    assert not result.valid
    assert result.reason == "FUTURE_DATA"


def test_rejects_insufficient_history():
    df = make_bars(date(2026, 7, 21), n=10)
    result = validate_daily_bars(df, date(2026, 7, 21))
    assert not result.valid
    assert result.reason == "INSUFFICIENT_HISTORY"


def test_rejects_inverted_high_low():
    df = make_bars(date(2026, 7, 21), n=130)
    df.loc[5, "high"] = df.loc[5, "low"] - 1.0
    result = validate_daily_bars(df, date(2026, 7, 21))
    assert not result.valid
    assert result.reason == "INVERTED_HIGH_LOW"


def test_accepts_valid_bars():
    df = make_bars(date(2026, 7, 21), n=130)
    result = validate_daily_bars(df, date(2026, 7, 21))
    assert result.valid
    assert result.reason is None
    assert result.rows == 130
    assert result.last_date == date(2026, 7, 21)


# ---------------- 冻结批次 ----------------


def test_freeze_batch_is_idempotent(db_session, fake_source):
    svc = MarketDataService(db_session, fake_source)
    first = svc.freeze_daily_batch(date(2026, 7, 21), MEMBERS)
    second = svc.freeze_daily_batch(date(2026, 7, 21), MEMBERS)
    assert second.batch_id == first.batch_id
    assert set(first.valid_symbols) == {"000001", "600000"}


def test_freeze_batch_partial_success_and_checksum_stable(db_session):
    as_of = date(2026, 7, 21)
    source = FakeSource(
        {
            "000001": (make_bars(as_of, 130, 10.0), "fake"),
            "600000": (make_bars(as_of, n=10, close=20.0), "fake"),  # 历史不足 -> 失败
        }
    )
    svc = MarketDataService(db_session, source)
    first = svc.freeze_daily_batch(as_of, MEMBERS)
    assert first.valid_symbols == ("000001",)
    assert first.failures["600000"] == "INSUFFICIENT_HISTORY"

    batch = db_session.get(MarketDataBatch, first.batch_id)
    assert batch.status == "SUCCESS"
    assert batch.checksum and len(batch.checksum) == 64

    bars = (
        db_session.query(DailyBar)
        .filter_by(market_data_batch_id=batch.id)
        .count()
    )
    assert bars == 130

    # 校验和稳定:对同一批有效数据(经相同归一化)重算应一致
    recomputed = MarketDataService._checksum(
        [("000001", normalize_daily_bars(source._data["000001"][0]))]
    )
    assert recomputed == batch.checksum