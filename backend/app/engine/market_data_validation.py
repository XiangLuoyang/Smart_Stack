"""市场数据归一化与校验。

将不同数据源的日 K 输出归一化为统一列(date/open/high/low/close/volume/adj_factor),
并在冻结为不可改写的 DailyBar 之前做完整性校验。校验失败的原因以稳定枚举返回,
供批次记录与前端故障状态展示。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

# 归一化后的标准列
CANONICAL_COLUMNS = ("date", "open", "high", "low", "close", "volume", "adj_factor")

# 各标准列可接受的原始列名(按小写匹配)
_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "date": ("date", "日期", "trade_date", "datetime"),
    "open": ("open", "开盘", "开盘价", "今开"),
    "high": ("high", "最高", "最高价"),
    "low": ("low", "最低", "最低价"),
    "close": ("close", "收盘", "收盘价", "最新价"),
    "volume": ("volume", "成交量", "vol", "成交额"),
    "adj_factor": ("adj_factor", "复权因子", "adjfactor", "qfq_factor"),
}

# 正式预测所需的最小历史行数
MIN_HISTORY_ROWS = 120


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    reason: str | None
    rows: int
    last_date: date | None


def normalize_daily_bars(df: pd.DataFrame) -> pd.DataFrame:
    """把任意来源的日 K DataFrame 归一化为标准列与类型。"""
    if df is None or df.empty:
        return pd.DataFrame(columns=list(CANONICAL_COLUMNS))

    work = df.reset_index() if df.index.name else df.copy()
    lowered = {str(c).strip().lower(): c for c in work.columns}

    out = pd.DataFrame()
    for canon, aliases in _COLUMN_ALIASES.items():
        series = None
        for alias in aliases:
            key = alias.lower()
            if key in lowered:
                series = work[lowered[key]]
                break
        out[canon] = series

    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.date
    for col in ("open", "high", "low", "close", "volume"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["adj_factor"] = pd.to_numeric(out["adj_factor"], errors="coerce").fillna(1.0)

    out = out.dropna(subset=["date", "open", "high", "low", "close"])
    out = out.sort_values("date").reset_index(drop=True)
    return out


def validate_daily_bars(df: pd.DataFrame, as_of: date) -> ValidationResult:
    """校验归一化日线是否可作为正式预测输入。

    失败原因(稳定枚举):
    - EMPTY: 无有效行
    - FUTURE_DATA: 存在晚于业务日的行
    - DUPLICATE_DATES: 存在重复日期
    - NONPOSITIVE_OHLC: OHLC 存在非正值
    - INVERTED_HIGH_LOW: 最高价低于最低价
    - STALE_DATA: 最新一根早于业务日
    - INSUFFICIENT_HISTORY: 历史行数不足 MIN_HISTORY_ROWS
    """
    norm = normalize_daily_bars(df)
    rows = len(norm)
    last_date = norm["date"].max() if rows else None

    if rows == 0:
        return ValidationResult(False, "EMPTY", 0, None)

    if any(d > as_of for d in norm["date"]):
        return ValidationResult(False, "FUTURE_DATA", rows, last_date)

    if norm["date"].duplicated().any():
        return ValidationResult(False, "DUPLICATE_DATES", rows, last_date)

    if (norm[["open", "high", "low", "close"]] <= 0).any().any():
        return ValidationResult(False, "NONPOSITIVE_OHLC", rows, last_date)

    if (norm["high"] < norm["low"]).any():
        return ValidationResult(False, "INVERTED_HIGH_LOW", rows, last_date)

    if last_date < as_of:
        return ValidationResult(False, "STALE_DATA", rows, last_date)

    if rows < MIN_HISTORY_ROWS:
        return ValidationResult(False, "INSUFFICIENT_HISTORY", rows, last_date)

    return ValidationResult(True, None, rows, last_date)