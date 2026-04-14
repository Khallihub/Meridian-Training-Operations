"""Structured JSON logging with per-request correlation IDs.

Usage
-----
Call ``configure_logging()`` once at application startup (done in main.py).
Add ``CorrelationIdMiddleware`` to the FastAPI app.

Within any log call you can attach extra context::

    logger.info("payment processed", extra={"job_id": "...", "order_id": "..."})

The ``request_id`` is injected automatically from the context variable set by
``CorrelationIdMiddleware``.
"""

from __future__ import annotations

import json
import logging
import uuid
from contextvars import ContextVar
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# ---------------------------------------------------------------------------
# Context variable — propagates the current request/job ID across async tasks
# ---------------------------------------------------------------------------

request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    return request_id_var.get("")


# ---------------------------------------------------------------------------
# JSON log formatter
# ---------------------------------------------------------------------------

_EXTRA_FIELDS = ("request_id", "job_id", "job_name", "source_id", "order_id", "user_id")


class StructuredJsonFormatter(logging.Formatter):
    """Emit every log record as a single JSON object on stdout/stderr.

    Standard fields emitted for every record:
    - ``timestamp`` — ISO-8601 UTC
    - ``level``
    - ``logger`` — dotted module name
    - ``message``
    - ``request_id`` — injected from context var (empty string when not in a request)

    Optional extra fields (included when present on the LogRecord):
    ``job_id``, ``job_name``, ``source_id``, ``order_id``, ``user_id``
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%(msecs)03dZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(""),
        }
        # Attach any extra context the caller passed via `extra={...}`
        for field in _EXTRA_FIELDS:
            val = getattr(record, field, None)
            if val is not None:
                payload[field] = val
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


# ---------------------------------------------------------------------------
# Configuration helper
# ---------------------------------------------------------------------------

def configure_logging(level: str = "INFO") -> None:
    """Replace the root handler with a StructuredJsonFormatter handler.

    Safe to call multiple times (idempotent — clears existing root handlers
    first so duplicate output is not produced).
    """
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJsonFormatter())
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


# ---------------------------------------------------------------------------
# ASGI middleware
# ---------------------------------------------------------------------------

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Inject a request-scoped correlation ID into the logging context var.

    - Reads ``X-Request-ID`` from the incoming request header when present;
      generates a fresh UUID4 otherwise.
    - Sets the ``request_id_var`` context variable for the lifetime of the
      request so all log calls within that request carry the same ID.
    - Echoes the ID back in the ``X-Request-ID`` response header so clients
      can correlate log entries with their own request logs.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_var.set(req_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_var.reset(token)
