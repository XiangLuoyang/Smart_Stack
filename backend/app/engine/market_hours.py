"""A 股交易时段判断。

简化版:周一至周五 9:30-11:30 / 13:00-15:00 视为交易时段。
节假日表硬编码当年(2026),后续可换 chinese_calendar 库。
"""
from __future__ import annotations

from datetime import date, datetime, time

# 简化节假日表(后续可换 chinese_calendar)
_HOLIDAYS_2026 = {
    # 元旦
    date(2026, 1, 1),
    # 春节(2.16-2.22)
    date(2026, 2, 16), date(2026, 2, 17), date(2026, 2, 18),
    date(2026, 2, 19), date(2026, 2, 20), date(2026, 2, 23), date(2026, 2, 24),
    # 清明(4.6-4.8)
    date(2026, 4, 6), date(2026, 4, 7), date(2026, 4, 8),
    # 劳动节(5.1-5.5)
    date(2026, 5, 1), date(2026, 5, 4), date(2026, 5, 5),
    # 端午(6.19-6.21)
    date(2026, 6, 19), date(2026, 6, 22), date(2026, 6, 23),
    # 中秋(9.25-9.27)
    date(2026, 9, 25), date(2026, 9, 28),
    # 国庆(10.1-10.8)
    date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 5),
    date(2026, 10, 6), date(2026, 10, 7), date(2026, 10, 8),
}

_MORNING_START = time(9, 30)
_MORNING_END = time(11, 30)
_AFTERNOON_START = time(13, 0)
_AFTERNOON_END = time(15, 0)


def is_holiday(d: date) -> bool:
    if d.year == 2026:
        return d in _HOLIDAYS_2026
    # 其他年份:只过滤周末,节假日表请按年补全
    return False


def is_trading_time(now: datetime | None = None) -> bool:
    """判断当前是否处于 A 股交易时段。"""
    now = now or datetime.now()
    if now.weekday() >= 5:  # 周六/周日
        return False
    if is_holiday(now.date()):
        return False
    t = now.time()
    in_morning = _MORNING_START <= t <= _MORNING_END
    in_afternoon = _AFTERNOON_START <= t <= _AFTERNOON_END
    return in_morning or in_afternoon
