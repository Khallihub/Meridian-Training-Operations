import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class RefundStatus(str, enum.Enum):
    requested = "requested"
    pending_review = "pending_review"
    approved = "approved"
    processing = "processing"
    completed = "completed"
    rejected = "rejected"
    failed = "failed"
    canceled = "canceled"


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (UniqueConstraint("external_event_id", name="uq_payments_external_event_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), unique=True, nullable=False, index=True)
    # Durable idempotency key provided by the payment gateway.  Nullable for
    # legacy/simulated callbacks that pre-date the field.
    external_event_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    terminal_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.pending, index=True)
    callback_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signature_verified: Mapped[bool] = mapped_column(nullable=False, default=False)
    raw_callback: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    refunds: Mapped[list["Refund"]] = relationship("Refund", back_populates="payment")


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False, index=True)
    requested_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[RefundStatus] = mapped_column(Enum(RefundStatus), nullable=False, default=RefundStatus.requested, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    payment: Mapped[Payment] = relationship("Payment", back_populates="refunds")


class ReconciliationExport(Base):
    __tablename__ = "reconciliation_exports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    export_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    row_count: Mapped[int] = mapped_column(nullable=False, default=0)
