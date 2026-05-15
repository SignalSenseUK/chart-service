from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.domain.schemas.chart_response import ErrorDetail, ErrorResponse

logger = get_logger("app.errors")


class DomainError(Exception):
    code: str = "internal_error"
    status_code: int = 500

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code:
            self.code = code
        self.message = message


class ChartNotFoundError(DomainError):
    code = "chart_not_found"
    status_code = status.HTTP_404_NOT_FOUND


class ChartDeletedError(DomainError):
    code = "chart_deleted"
    status_code = status.HTTP_410_GONE


_HTTP_422 = 422


class ChartValidationError(DomainError):
    code = "validation_error"
    status_code = _HTTP_422


class ChartConflictError(DomainError):
    code = "conflict"
    status_code = status.HTTP_409_CONFLICT


class ProviderError(DomainError):
    code = "provider_error"
    status_code = status.HTTP_502_BAD_GATEWAY


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump())


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    logger.info(
        "domain.error",
        code=exc.code,
        message=exc.message,
        path=str(request.url.path),
        status_code=exc.status_code,
    )
    return _error_response(exc.code, exc.message, exc.status_code)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors: list[dict[str, Any]] = exc.errors()
    if errors:
        first = errors[0]
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        message = first.get("msg", "validation error")
        if loc:
            message = f"{loc}: {message}"
    else:
        message = "validation error"
    return _error_response("invalid_request", message, _HTTP_422)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from app.core.config import get_settings

    settings = get_settings()
    if settings.APP_ENV == "production":
        message = "internal server error"
    else:
        message = f"{exc.__class__.__name__}: {exc}"
    logger.error(
        "unhandled.exception",
        path=str(request.url.path),
        error_type=exc.__class__.__name__,
        error=str(exc),
    )
    return _error_response("internal_error", message, 500)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
