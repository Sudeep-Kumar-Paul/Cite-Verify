from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class CiteVerifyException(Exception):
    def __init__(self, message: str, status_code: int = 500, detail: str = ""):
        self.message = message
        self.status_code = status_code
        self.detail = detail or message
        super().__init__(message)


class DocumentNotFoundException(CiteVerifyException):
    def __init__(self, document_id: str):
        super().__init__(
            message=f"Document '{document_id}' not found.",
            status_code=404,
            detail=f"No document with id '{document_id}' exists in the database.",
        )


class ProcessingException(CiteVerifyException):
    def __init__(self, message: str, detail: str = ""):
        super().__init__(message=message, status_code=422, detail=detail)


class ExternalAPIException(CiteVerifyException):
    def __init__(self, service: str, message: str, detail: str = ""):
        super().__init__(
            message=f"External API error ({service}): {message}",
            status_code=503,
            detail=detail or message,
        )


class ValidationException(CiteVerifyException):
    def __init__(self, message: str, detail: str = ""):
        super().__init__(message=message, status_code=400, detail=detail)


class InsufficientEvidenceException(CiteVerifyException):
    def __init__(self, claim_id: str, reason: str):
        super().__init__(
            message=f"Insufficient evidence to verify claim '{claim_id}': {reason}",
            status_code=200,
            detail=reason,
        )


def add_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(CiteVerifyException)
    async def citeverify_exception_handler(request: Request, exc: CiteVerifyException) -> JSONResponse:
        logger.warning(f"CiteVerifyException: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": type(exc).__name__,
                "detail": exc.detail,
                "status_code": exc.status_code,
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "detail": "An unexpected error occurred. Please try again.",
                "status_code": 500,
            },
        )
