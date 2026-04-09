"""Keyset-based pagination utilities."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PageMeta(BaseModel):
    total_count: int
    page: int
    page_size: int
    has_next: bool
    query_time_ms: float | None = None


class Page(BaseModel, Generic[T]):
    items: list[T]
    meta: PageMeta


def paginate_query(query: Any, page: int, page_size: int) -> tuple[Any, int, int]:
    """Return (query_with_limit_offset, offset, limit)."""
    from app.core.config import settings
    page_size = min(page_size, settings.MAX_PAGE_SIZE)
    offset = (page - 1) * page_size
    return query.offset(offset).limit(page_size), offset, page_size
