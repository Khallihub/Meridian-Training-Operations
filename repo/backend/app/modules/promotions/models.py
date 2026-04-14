import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PromotionType(str, enum.Enum):
    percent_off = "percent_off"
    fixed_off = "fixed_off"
    threshold_fixed_off = "threshold_fixed_off"
    bogo_selected_workshops = "bogo_selected_workshops"


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[PromotionType] = mapped_column(Enum(PromotionType), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    min_order_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    applies_to: Mapped[dict] = mapped_column(JSONB, nullable=False, default=lambda: {"all": True})
    # Tie-break ordering: lower value = higher precedence (applied when two promos
    # yield the same discount).  Default 0 so existing records rank equally.
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    stack_group: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_exclusive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
