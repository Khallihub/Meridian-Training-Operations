import json
import uuid
from datetime import datetime, UTC

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware


class AppError(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found.", status.HTTP_404_NOT_FOUND)


class UnauthorizedError(AppError):
    def __init__(self, detail: str = "Not authenticated."):
        super().__init__(detail, status.HTTP_401_UNAUTHORIZED)


class AccountLockedError(AppError):
    def __init__(self, locked_until: datetime):
        super().__init__("Account locked.", status.HTTP_423_LOCKED)
        self.locked_until = locked_until.isoformat()


class ForbiddenError(AppError):
    def __init__(self, detail: str = "Insufficient permissions."):
        super().__init__(detail, status.HTTP_403_FORBIDDEN)


class GoneError(AppError):
    def __init__(self, detail: str = "Resource no longer available."):
        super().__init__(detail, status.HTTP_410_GONE)


class ConflictError(AppError):
    def __init__(self, detail: str = "Conflict."):
        super().__init__(detail, status.HTTP_409_CONFLICT)


class UnprocessableError(AppError):
    def __init__(self, detail: str = "Unprocessable."):
        super().__init__(detail, status.HTTP_422_UNPROCESSABLE_ENTITY)


def _make_meta(request_id: str) -> dict:
    return {
        "request_id": request_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "v1",
    }


class ResponseEnvelopeMiddleware(BaseHTTPMiddleware):
    """Wrap all JSON API responses in the standard PRD envelope:
    { "data": <payload>, "meta": { "request_id", "timestamp", "version" }, "error": null }
    Error responses become: { "data": null, "meta": ..., "error": { "code", "message", "details" } }
    Non-JSON, non-API, and streaming responses pass through unchanged.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)

        # Only wrap /api/v1/* responses that are JSON
        path = request.url.path
        content_type = response.headers.get("content-type", "")
        if not path.startswith("/api/v1") or "application/json" not in content_type:
            return response

        # Read and re-wrap the response body
        body_bytes = b""
        async for chunk in response.body_iterator:
            body_bytes += chunk

        try:
            original = json.loads(body_bytes)
        except (json.JSONDecodeError, ValueError):
            return Response(content=body_bytes, status_code=response.status_code, headers=dict(response.headers))

        meta = _make_meta(request_id)

        if response.status_code >= 400:
            # Error shape — surface detail/message from FastAPI/app error handlers
            detail = original.get("detail")
            if isinstance(detail, list):
                # Pydantic validation errors: list of {loc, msg, type}
                message = "; ".join(e.get("msg", str(e)) for e in detail)
                details = [{"field": ".".join(str(x) for x in e.get("loc", [])), "issue": e.get("msg", "")} for e in detail]
            elif isinstance(detail, str):
                message = detail
                details = []
            else:
                message = original.get("message", "An error occurred.")
                details = []
            error_code = {
                400: "BAD_REQUEST",
                401: "UNAUTHORIZED",
                403: "FORBIDDEN",
                404: "NOT_FOUND",
                409: "CONFLICT",
                410: "GONE",
                422: "VALIDATION_ERROR",
                423: "ACCOUNT_LOCKED",
                500: "INTERNAL_SERVER_ERROR",
            }.get(response.status_code, "ERROR")
            envelope = {
                "data": None,
                "meta": meta,
                "error": {
                    "code": error_code,
                    "message": message,
                    "details": details,
                },
            }
            if "locked_until" in original.get("errors", {}):
                envelope["error"]["details"].append({"field": "locked_until", "issue": original["errors"]["locked_until"]})
        else:
            envelope = {"data": original, "meta": meta, "error": None}

        wrapped = json.dumps(envelope)
        new_headers = dict(response.headers)
        new_headers["content-length"] = str(len(wrapped.encode()))
        return Response(
            content=wrapped,
            status_code=response.status_code,
            headers=new_headers,
            media_type="application/json",
        )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_middleware(ResponseEnvelopeMiddleware)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        content: dict = {"detail": exc.message}
        if isinstance(exc, AccountLockedError):
            content["errors"] = {"locked_until": exc.locked_until}
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        # exc.errors() from Pydantic v2 may include a raw Exception object under
        # the 'ctx' key (e.g. ctx={'error': ValueError(...)}) which is not JSON-
        # serializable and causes JSONResponse to raise TypeError.  Stringify it.
        sanitized = []
        for err in exc.errors():
            ctx = err.get("ctx")
            if isinstance(ctx, dict) and isinstance(ctx.get("error"), Exception):
                err = {**err, "ctx": {**ctx, "error": str(ctx["error"])}}
            sanitized.append(err)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": sanitized},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred."},
        )
