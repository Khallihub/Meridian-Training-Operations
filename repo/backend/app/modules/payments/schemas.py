import uuid
from datetime import datetime

from pydantic import BaseModel

from app.modules.payments.models import PaymentStatus, RefundStatus


class PaymentCallbackPayload(BaseModel):
    order_id: uuid.UUID
    terminal_ref: str
    amount: float
    timestamp: str       # ISO8601 string used in HMAC
    signature: str       # HMAC-SHA256 hex


class PaymentResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    terminal_ref: str | None
    amount: float
    status: PaymentStatus
    callback_received_at: datetime | None
    signature_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RefundCreate(BaseModel):
    order_id: uuid.UUID
    amount: float
    reason: str | None = None


class RefundResponse(BaseModel):
    id: uuid.UUID
    payment_id: uuid.UUID
    requested_by: uuid.UUID
    amount: float
    reason: str | None
    status: RefundStatus
    created_at: datetime
    processed_at: datetime | None

    model_config = {"from_attributes": True}


class ReconciliationExportResponse(BaseModel):
    id: uuid.UUID
    export_date: datetime
    file_path: str
    generated_at: datetime
    row_count: int

    model_config = {"from_attributes": True}
