"""沪深300选股服务:从 akshare 拉成分股,对每只计算预期年化收益,排序输出 Top N。

- 池子来源: ak.index_stock_cons_csindex("000300") -> 300 只成分股(含代码+名称)
- 评分: 复用 src.models.prediction.ReturnPredictor.calculate_expected_return
- 任务化: scan 启动后台线程, status 轮询进度,结果存内存 + data/screener_result.json
"""
from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.config import DATA_DIR

logger = logging.getLogger(__name__)

_RESULT_FILE = DATA_DIR / "screener_result.json"
_LOCK = threading.Lock()


class ScreenerJob:
    """单例选股任务:同时只允许一个 scan 在跑。"""

    def __init__(self) -> None:
        self.running = False
        self.progress_total = 0
        self.progress_done = 0
        self.current_symbol = ""
        self.started_at: Optional[float] = None
        self.finished_at: Optional[float] = None
        self.error: Optional[str] = None
        self.result: Optional[dict] = None

    # ---- 池子 ----
    def fetch_hs300_constituents(self) -> list[dict]:
        """返回 [{code, name}],失败抛异常。"""
        import akshare as ak
        df = ak.index_stock_cons_csindex(symbol="000300")
        if df is None or df.empty:
            return []
        # 列名是中文,按位置或宽松匹配取「成分券代码」「成分券名称」
        cols = list(df.columns)
        code_col = next((c for c in cols if "代码" in str(c)), cols[4] if len(cols) > 4 else cols[0])
        name_col = next((c for c in cols if "名称" in str(c)), cols[5] if len(cols) > 5 else cols[1])
        out = []
        for _, row in df.iterrows():
            code = str(row.get(code_col, "")).strip()
            name = str(row.get(name_col, "")).strip()
            if code and name:
                out.append({"code": code, "name": name})
        return out

    # ---- 启动 ----
    def start(self, top_n: int = 10, min_data_points: int = 60) -> str:
        """启动后台扫描。返回 "started" / "already_running"。"""
        with _LOCK:
            if self.running:
                return "already_running"
            self.running = True
            self.progress_done = 0
            self.progress_total = 0
            self.current_symbol = ""
            self.started_at = time.time()
            self.finished_at = None
            self.error = None
            self.result = None
        t = threading.Thread(target=self._run, args=(top_n, min_data_points), daemon=True)
        t.start()
        logger.info("沪深300选股任务已启动")
        return "started"

    def _run(self, top_n: int, min_data_points: int) -> None:
        try:
            from src.models.prediction import ReturnPredictor
            pool = self.fetch_hs300_constituents()
            with _LOCK:
                self.progress_total = len(pool)
            logger.info("沪深300成分股拉取成功: %d 只", len(pool))

            predictor = ReturnPredictor()
            scored: list[dict] = []
            start_date = datetime(2020, 1, 1)

            for i, item in enumerate(pool):
                code = item["code"]
                name = item["name"]
                with _LOCK:
                    self.progress_done = i
                    self.current_symbol = code
                try:
                    res = predictor.calculate_expected_return(code, start_date, 30, 0.95)
                    if res.get("error"):
                        continue
                    if (res.get("data_points") or 0) < min_data_points:
                        continue
                    scored.append({
                        "code": code,
                        "name": name,
                        "score": float(res.get("annualized_return") or res.get("expected_daily_return") or 0.0),
                        "daily_return": float(res.get("expected_daily_return") or 0.0),
                        "daily_std": float(res.get("daily_std") or 0.0),
                        "method": res.get("method", "statistical"),
                        "data_points": res.get("data_points"),
                        "ci": res.get("confidence_interval"),
                    })
                except Exception as e:
                    logger.debug("选股评分失败 %s: %s", code, e)

            with _LOCK:
                self.progress_done = len(pool)
                self.current_symbol = ""

            scored.sort(key=lambda x: x["score"], reverse=True)
            buy = scored[:top_n]
            sell = list(reversed(scored[-top_n:])) if len(scored) >= top_n else list(reversed(scored))

            payload = {
                "pool": "HS300",
                "pool_size": len(pool),
                "scored_count": len(scored),
                "started_at": datetime.fromtimestamp(self.started_at or 0).isoformat(),
                "finished_at": datetime.now().isoformat(),
                "buy": buy,
                "sell": sell,
            }
            with _LOCK:
                self.result = payload
                self.finished_at = time.time()
                self.running = False
            try:
                _RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)
                _RESULT_FILE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            except Exception as e:
                logger.warning("写选股结果文件失败: %s", e)
            logger.info("沪深300选股完成: 评分 %d 只, buy %d sell %d", len(scored), len(buy), len(sell))
        except Exception as e:
            logger.error("选股任务异常: %s", e, exc_info=True)
            with _LOCK:
                self.error = str(e)
                self.running = False
                self.finished_at = time.time()

    # ---- 状态查询 ----
    def status(self) -> dict:
        with _LOCK:
            base = {
                "running": self.running,
                "progress_done": self.progress_done,
                "progress_total": self.progress_total,
                "current_symbol": self.current_symbol,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "error": self.error,
            }
        # 如果内存里没结果但磁盘有(进程重启后),尝试加载
        if self.result is None and not self.running and _RESULT_FILE.exists():
            try:
                base["result"] = json.loads(_RESULT_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        else:
            base["result"] = self.result
        return base


_singleton: Optional[ScreenerJob] = None


def get_screener() -> ScreenerJob:
    global _singleton
    if _singleton is None:
        _singleton = ScreenerJob()
    return _singleton