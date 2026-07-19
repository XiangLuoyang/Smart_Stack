"""ORM 公共混入:时间戳 + 主键。"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )


def gen_uuid() -> str:
    return uuid.uuid4().hex


class UUIDPk:
    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=gen_uuid
    )
