"""行情服务:内存缓存 + 持久化快照 + 数据源适配。

对外暴露 get_quote / get_quotes / get_kline / update_quotes。
数据源复用旧 src/data/smart_loader.py(经 MarketDataAdaptor 包装)。
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Iterable

import pandas as pd
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.engine.matching import Quote
from app.models.market_snapshot import MarketSnapshot

logger = logging.getLogger(__name__)


class MarketDataAdaptor:
    """适配旧 smart_loader / loader_akshare,避免循环导入。

    延迟导入旧 src/ 模块,失败时回退到 yfinance。
    """

    def __init__(self):
        self._loader = None
        self._akshare_loader = None

    def _ensure_loader(self):
        if self._loader is not None:
            return
        try:
            # 优先用 akshare(A 股更准),失败回退到 smart_loader
            from src.data.loader_akshare import AKShareDataLoader
            self._akshare_loader = AKShareDataLoader()
        except Exception as e:
            logger.warning(f"akshare 加载失败,回退到 smart_loader: {e}")
        try:
            from src.config.settings import DataConfig
            from src.data.smart_loader import get_smart_loader
            self._loader = get_smart_loader(DataConfig())
        except Exception as e:
            logger.warning(f"smart_loader 加载失败: {e}")
            self._loader = None

    def load_kline(
        self, symbol: str, start_date: str | None = None, end_date: str | None = None
    ) -> tuple[pd.DataFrame, str]:
        self._ensure_loader()
        # A 股代码(纯数字)优先走 akshare
        code = symbol.upper().split(".")[0]
        if self._akshare_loader and code.isdigit() and len(code) == 6:
            df, std = self._akshare_loader.load_stock_data(symbol, "daily", start_date, end_date)
            if not df.empty:
                return df, std
        if self._loader:
            return self._loader.load_stock_data(symbol, "daily", start_date, end_date)
        return pd.DataFrame(), symbol

    def get_realtime(self, symbol: str) -> dict | None:
        self._ensure_loader()
        try:
            if self._akshare_loader and hasattr(self._akshare_loader, "get_real_time_quote"):
                return self._akshare_loader.get_real_time_quote(symbol)
        except Exception as e:
            logger.debug(f"akshare realtime 失败 {symbol}: {e}")
        return None


class MarketService:
    """内存行情缓存 + 持久化快照。"""

    def __init__(self, db: Session):
        self.db = db
        self._cache: dict[str, Quote] = {}
        self._lock = threading.RLock()
        self.adaptor = MarketDataAdaptor()

    # ---------------- 内存行情 ----------------

    def get_quote(self, symbol: str) -> Quote | None:
        with self._lock:
            return self._cache.get(symbol)

    def get_quotes(self, symbols: Iterable[str]) -> dict[str, Quote]:
        syms = list(symbols)
        with self._lock:
            return {s: self._cache[s] for s in syms if s in self._cache}

    def update_quote(self, quote: Quote) -> None:
        with self._lock:
            self._cache[quote.symbol] = quote

    def all_symbols(self) -> list[str]:
        with self._lock:
            return list(self._cache.keys())

    # ---------------- 拉取 + 持久化 ----------------

    def refresh_quote(self, symbol: str) -> Quote | None:
        """从数据源拉一次最新价,写入内存 + 快照表。"""
        try:
            rt = self.adaptor.get_realtime(symbol)
            price = None
            ts = datetime.now()
            prev_close = None
            if rt:
                # akshare 返回字段名因版本而异,做容错
                price = (
                    rt.get("price")
                    or rt.get("最新价")
                    or rt.get("close")
                    or rt.get("current")
                )
                prev_close = rt.get("昨收") or rt.get("prev_close")
            if price is None:
                # 回退:取最近一根日 K 的收盘
                df, _ = self.adaptor.load_kline(symbol)
                if not df.empty and "Close" in df.columns:
                    last = df.iloc[-1]
                    price = float(last["Close"])
                    ts = pd.to_datetime(last.get("Date", ts)).to_pydatetime() if "Date" in last else ts
                    if len(df) >= 2:
                        prev_close = float(df.iloc[-2]["Close"])
            if price is None:
                logger.warning(f"无法获取 {symbol} 行情")
                return None

            quote = Quote(symbol=symbol, price=float(price), ts=ts)
            self.update_quote(quote)

            # 持久化快照
            snap = MarketSnapshot(
                symbol=symbol,
                ts=ts,
                open=float(price),
                high=float(price),
                low=float(price),
                close=float(price),
                volume=0.0,
                prev_close=float(prev_close) if prev_close else None,
            )
            self.db.add(snap)
            self.db.commit()
            return quote
        except Exception as e:
            logger.error(f"刷新行情失败 {symbol}: {e}", exc_info=True)
            self.db.rollback()
            return None

    def refresh_many(self, symbols: Iterable[str]) -> dict[str, Quote]:
        result: dict[str, Quote] = {}
        for s in symbols:
            q = self.refresh_quote(s)
            if q:
                result[s] = q
        return result

    # ---------------- K 线 ----------------

    def get_kline(self, symbol: str, days: int = 120) -> pd.DataFrame:
        """取最近 N 天日 K,补上技术指标。"""
        from app.engine.technical import TechnicalIndicatorCalculator

        df, _ = self.adaptor.load_kline(symbol)
        if df.empty:
            return df
        df = df.tail(days).reset_index(drop=True)
        calc = TechnicalIndicatorCalculator()
        return calc.add_all_indicators(df)

    def latest_snapshot(self, symbol: str) -> MarketSnapshot | None:
        stmt = (
            select(MarketSnapshot)
            .where(MarketSnapshot.symbol == symbol)
            .order_by(desc(MarketSnapshot.ts))
            .limit(1)
        )
        return self.db.scalars(stmt).first()
