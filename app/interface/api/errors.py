from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AuthenticationError,
    ExternalServiceError,
    NotFoundError,
    UnsupportedMediaTypeError,
    ValidationError,
)


def _error(detail: str) -> dict:
    return {"detail": detail}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content=_error(str(exc)))

    @app.exception_handler(UnsupportedMediaTypeError)
    async def _unsupported(_: Request, exc: UnsupportedMediaTypeError) -> JSONResponse:
        return JSONResponse(status_code=400, content=_error(str(exc)))

    @app.exception_handler(ValidationError)
    async def _validation(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content=_error(str(exc)))

    @app.exception_handler(AuthenticationError)
    async def _authentication(_: Request, exc: AuthenticationError) -> JSONResponse:
        return JSONResponse(status_code=401, content=_error(str(exc)))

    @app.exception_handler(ExternalServiceError)
    async def _external(_: Request, exc: ExternalServiceError) -> JSONResponse:
        return JSONResponse(status_code=502, content=_error(str(exc)))
