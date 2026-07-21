"""交易日历测试:按交易日而非自然日偏移。"""
from __future__ import annotations

from datetime import date


def test_shift_counts_sessions_not_calendar_days(calendar):
    # 国庆 10/1-10/7 休市,第 10 个交易日跨过假期落到 10/16
    assert calendar.shift(date(2026, 9, 25), 10) == date(2026, 10, 16)


def test_sessions_after_returns_n_sessions(calendar):
    sessions = calendar.sessions_after(date(2026, 7, 21), 10)
    assert len(sessions) == 10
    assert sessions[-1] == date(2026, 8, 4)


def test_shift_skips_weekends(calendar):
    # 2026-07-24 是周五,下一个交易日是周一 07-27
    assert calendar.shift(date(2026, 7, 24), 1) == date(2026, 7, 27)