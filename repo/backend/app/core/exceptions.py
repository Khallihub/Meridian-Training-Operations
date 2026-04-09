from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status


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


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        content: dict = {"detail": exc.message}
        if isinstance(exc, AccountLockedError):
            content["errors"] = {"locked_until": exc.locked_until}
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred."},
        )
