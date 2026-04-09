import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator

from app.modules.promotions.models import PromotionType


class PromotionCreate(BaseModel):
    name: str
    type: PromotionType
    value: float
    min_order_amount: float | None = None
    applies_to: dict = {"all": True}
    stack_group: str | None = None
    is_exclusive: bool = False
    valid_from: datetime
    valid_until: datetime

    @field_validator("applies_to", mode="before")
    @classmethod
    def coerce_applies_to(cls, v: Any) -> dict:
        if isinstance(v, str):
            return {"all": True} if v == "all" else {v: True}
        return v


class PromotionUpdate(BaseModel):
    name: str | None = None
    value: float | None = None
    min_order_amount: float | None = None
    applies_to: dict | None = None
    stack_group: str | None = None
    is_exclusive: bool | None = None
    is_active: bool | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None

    @field_validator("applies_to", mode="before")
    @classmethod
    def coerce_applies_to(cls, v: Any) -> dict | None:
        if isinstance(v, str):
            return {"all": True} if v == "all" else {v: True}
        return v


class PromotionResponse(BaseModel):
    id: uuid.UUID
    name: str
    type: PromotionType
    value: float
    min_order_amount: float | None
    applies_to: dict
    stack_group: str | None
    is_exclusive: bool
    is_active: bool
    valid_from: datetime
    valid_until: datetime

    model_config = {"from_attributes": True}
