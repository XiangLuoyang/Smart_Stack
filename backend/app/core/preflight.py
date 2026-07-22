"""启动预检:验证本地配置,FAILED 阻止启动,DEGRADED 允许但警告。"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PreflightReport:
    status: str  # OK / DEGRADED / FAILED
    codes: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)


def run_preflight(data_dir: str | None = None, llm_api_key: str | None = None) -> PreflightReport:
    codes: list[str] = []
    details: list[str] = []
    failed = False
    degraded = False

    if sys.version_info < (3, 12):
        codes.append("PYTHON_VERSION_LOW")
        details.append(f"Python {sys.version_info.major}.{sys.version_info.minor} < 3.12")
        failed = True

    base = Path(data_dir) if data_dir else Path(__file__).resolve().parents[2] / "data"
    if not base.exists():
        try:
            base.mkdir(parents=True, exist_ok=True)
        except OSError:
            codes.append("DATA_DIR_NOT_WRITABLE")
            details.append(f"Cannot create {base}")
            failed = True
    elif not os.access(str(base), os.W_OK):
        codes.append("DATA_DIR_NOT_WRITABLE")
        details.append(f"{base} is not writable")
        failed = True

    if not llm_api_key:
        codes.append("LLM_DISABLED")
        details.append("LLM_API_KEY not set; LLM features unavailable")
        degraded = True

    status = "FAILED" if failed else ("DEGRADED" if degraded else "OK")
    return PreflightReport(status=status, codes=codes, details=details)