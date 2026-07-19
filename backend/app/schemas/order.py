from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Side = Literal["BUY", "SELL"]
OrderType = Literal["MARKET", "LIMIT"]
OrderStatus = Literal["PENDING", "FILLED", "CANCELLED", "REJECTED"]


class OrderCreate(BaseModel):
    account_id: str
    symbol: str = Field(..., min_length=1, max_length=32)
    side: Side
    qty: float = Field(..., gt=0)
    order_type: OrderType = "MARKET"
    price: float | None = Field(default=None, gt=0)


class OrderOut(BaseModel):
    id: str
    account_id: str
    symbol: str
    side: Side
    order_type: OrderType
    qty: float
    price: float | None
    filled_qty: float
    filled_price: float | None
    status: OrderStatus
    reject_reason: str | None = None
    created_at: datetime
    filled_at: datetime | None = None

    model_config = {"from_attributes": True}


class TradeOut(BaseModel):
    id: str
    order_id: str
    account_id: str
    symbol: str
    side: Side
    qty: float
    price: float
    commission: float
    stamp_duty: float
    transfer_fee: float
    total_cost: float
    filled_at: datetime

    model_config = {"from_attributes": True}


class PlaceOrderResultOut(BaseModel):
    accepted: bool
    message: str
    order: OrderOut | None = None
    trade: TradeOut | None = None
