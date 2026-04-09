"""Utility functions for masking sensitive fields in API responses."""

import re


def mask_phone(phone: str | None) -> str | None:
    """Return masked phone: +1-***-***-1234 style."""
    if not phone:
        return phone
    digits = re.sub(r"\D", "", phone)
    if len(digits) >= 4:
        return f"***-***-{digits[-4:]}"
    return "***"


def mask_email(email: str | None) -> str | None:
    """Return masked email: f***@domain.com style."""
    if not email or "@" not in email:
        return email
    local, domain = email.rsplit("@", 1)
    if len(local) <= 2:
        return f"{'*' * len(local)}@{domain}"
    return f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}@{domain}"
