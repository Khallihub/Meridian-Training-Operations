from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.checkout.models import OrderStatus


class CartItemInput(BaseModel):
    session_id: uuid.UUID
    quantity: int = Field(default=1, ge=1, le=100)


class CartCreate(BaseModel):
    items: list[CartItemInput]


class AppliedPromotionDetail(BaseModel):
    promotion_id: uuid.UUID
    promotion_name: str
    discount_amount: float
    explanation: str


class OrderItemResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    session_title: str | None = None
    unit_price: float
    quantity: int

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: uuid.UUID
    learner_id: uuid.UUID
    status: OrderStatus
    subtotal: float
    discount_total: float
    total: float
    currency: str
    created_at: datetime
    paid_at: datetime | None
    expires_at: datetime | None
    items: list[OrderItemResponse] = []
    applied_promotions: list[AppliedPromotionDetail] = []

    model_config = {"from_attributes": True}


class BestOfferResponse(BaseModel):
    subtotal: float
    discount_total: float
    total: float
    applied_promotions: list[AppliedPromotionDetail]
