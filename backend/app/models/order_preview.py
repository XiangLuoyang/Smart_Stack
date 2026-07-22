"""订单预览:两步确认的第一步,60秒过期。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models._mixins import TimestampMixin, UUIDPk

PREVIEW_TTL_SECONDS = 60


class OrderPreview(Base, UUIDPk, TimestampMixin):
    __tablename__ = "order_previews"

    account_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    order_type: Mapped[str] = mapped_column(String(8), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    research_case_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    decision_entry_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quote_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    quote_ts: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fee_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    lower_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    upper_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    confirmation_token: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    confirmed: Mapped[bool] = mapped_column(default=False, nullable=False)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)