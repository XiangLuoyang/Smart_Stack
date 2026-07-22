"""结构化日志:JSON 格式 + 敏感字段脱敏。"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

SENSITIVE_PATTERN = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD)", re.IGNORECASE)


class RedactingJsonFormatter(logging.Formatter):
    """JSON 日志格式化器,自动脱敏含 KEY/TOKEN/SECRET/PASSWORD 的字段。"""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "run_id"):
            entry["run_id"] = record.run_id
        if hasattr(record, "task_type"):
            entry["task_type"] = record.task_type
        if record.exc_info and record.exc_info[0]:
            entry["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            for key, value in record.extra_data.items():
                if SENSITIVE_PATTERN.search(key):
                    entry[key] = "***REDACTED***"
                else:
                    entry[key] = value

        return json.dumps(entry, ensure_ascii=False, default=str)


def setup_structured_logging(level: int = logging.INFO) -> None:
    """配置全局结构化日志。"""
    handler = logging.StreamHandler()
    handler.setFormatter(RedactingJsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)