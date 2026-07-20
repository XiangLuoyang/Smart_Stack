"""A-share code->name mapping service, backed by akshare with local JSON cache."""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Optional

from app.core.config import DATA_DIR

logger = logging.getLogger(__name__)

_CACHE_FILE = DATA_DIR / "a_share_names.json"
_CACHE_TTL = 12 * 3600  # 12 hours
_LOCK = threading.Lock()


class SymbolService:
    """Full A-share (code -> name) map, persisted to data/a_share_names.json."""

    def __init__(self) -> None:
        self._names: dict = {}
        self._loaded_at: float = 0.0
        self._loaded = False

    def _load_disk(self) -> None:
        if not _CACHE_FILE.exists():
            return
        try:
            self._names = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            self._loaded_at = _CACHE_FILE.stat().st_mtime
            self._loaded = True
            logger.info("loaded stock names from disk: %d entries", len(self._names))
        except Exception as e:
            logger.warning("failed to load name cache: %s", e)

    def _fetch_remote(self) -> None:
        try:
            import akshare as ak
            df = ak.stock_info_a_code_name()
            if df is None or df.empty:
                return
            mapping = {}
            for _, row in df.iterrows():
                code = str(row.get("code", "")).strip()
                name = str(row.get("name", "")).strip()
                if code and name:
                    mapping[code] = name
            if not mapping:
                return
            self._names = mapping
            self._loaded_at = time.time()
            self._loaded = True
            _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            _CACHE_FILE.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
            logger.info("fetched and cached stock names: %d entries", len(mapping))
        except Exception as e:
            logger.warning("akshare name fetch failed: %s", e)

    def ensure_loaded(self) -> None:
        with _LOCK:
            if not self._loaded:
                self._load_disk()
            if not self._names or (time.time() - self._loaded_at) > _CACHE_TTL:
                self._fetch_remote()

    def get_name(self, code: str) -> str:
        if not code:
            return ""
        c = code.strip().upper().split(".")[0]
        self.ensure_loaded()
        return self._names.get(c, "")

    def get_names(self, codes: list) -> dict:
        return {c: self.get_name(c) for c in codes if c}

    def search(self, keyword: str, limit: int = 20) -> list:
        if not keyword:
            return []
        self.ensure_loaded()
        kw = keyword.strip()
        results = []
        for code, name in self._names.items():
            if code.startswith(kw) or kw in name:
                results.append({"code": code, "name": name})
                if len(results) >= limit:
                    break
        return results


_singleton: Optional[SymbolService] = None


def get_symbol_service() -> SymbolService:
    global _singleton
    if _singleton is None:
        _singleton = SymbolService()
    return _singleton