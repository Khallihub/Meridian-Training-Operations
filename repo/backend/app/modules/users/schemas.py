import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from app.core.masking import mask_email, mask_phone
from app.core.security import validate_password_complexity
from app.modules.users.models import UserRole


class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole
    email: str | None = None
    phone: str | None = None

    @field_validator("password")
    @classmethod
    def validate_pw(cls, v: str) -> str:
        validate_password_complexity(v)
        return v


class UserUpdate(BaseModel):
    email: str | None = None
    phone: str | None = None
    is_active: bool | None = None
    role: UserRole | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    role: UserRole
    email: str | None = None      # masked
    phone: str | None = None      # masked
    is_active: bool
    last_login: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserDetailResponse(UserResponse):
    """Admin-only: same masked view as UserResponse.

    Unmasked PII is only available via the dedicated POST /users/{id}/unmask
    endpoint, which requires an explicit reason and emits an audit event.
    """


class UserUnmaskResponse(BaseModel):
    """Returned exclusively by the /unmask endpoint."""
    id: uuid.UUID
    username: str
    email_unmasked: str | None = None
    phone_unmasked: str | None = None
    reason: str

    model_config = {"from_attributes": True}
