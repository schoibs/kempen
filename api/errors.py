from __future__ import annotations

import logging

from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException


logger = logging.getLogger(__name__)


class ApiProblem(Exception):
    def __init__(self, *, status: int, code: str, title: str, detail: str) -> None:
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail


def problem_handler(_: Request, error: ApiProblem) -> JSONResponse:
    return _problem_response(
        status=error.status,
        code=error.code,
        title=error.title,
        detail=error.detail,
        errors=[],
    )


def validation_problem_handler(_: Request, error: RequestValidationError) -> JSONResponse:
    return _problem_response(
        status=422,
        code="VALIDATION_ERROR",
        title="Request validation failed",
        detail="One or more request fields are invalid.",
        errors=[
            {"location": list(item["loc"]), "message": item["msg"]}
            for item in error.errors()
        ],
    )


def http_problem_handler(_: Request, error: StarletteHTTPException) -> JSONResponse:
    if error.status_code == 404:
        return _problem_response(
            status=404,
            code="NOT_FOUND",
            title="Resource not found",
            detail="The requested resource does not exist.",
            errors=[],
        )
    if error.status_code == 503:
        return _problem_response(
            status=503,
            code="SERVICE_UNAVAILABLE",
            title="Service unavailable",
            detail="The service is temporarily unavailable.",
            errors=[],
        )
    return _problem_response(
        status=error.status_code,
        code="HTTP_ERROR",
        title="Request could not be completed",
        detail="The request could not be completed.",
        errors=[],
    )


def database_problem_handler(_: Request, error: SQLAlchemyError) -> JSONResponse:
    logger.error("Database request failed: %s", type(error).__name__)
    return _problem_response(
        status=503,
        code="SERVICE_UNAVAILABLE",
        title="Campaign service unavailable",
        detail="The campaign service is temporarily unavailable.",
        errors=[],
    )


def internal_problem_handler(_: Request, error: Exception) -> JSONResponse:
    logger.error("Unhandled API error: %s", type(error).__name__)
    return _problem_response(
        status=500,
        code="INTERNAL_ERROR",
        title="Internal server error",
        detail="The request could not be completed.",
        errors=[],
    )


def _problem_response(
    *,
    status: int,
    code: str,
    title: str,
    detail: str,
    errors: list[dict[str, object]],
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "type": f"https://api.example.com/problems/{code.lower().replace('_', '-')}",
            "title": title,
            "status": status,
            "code": code,
            "detail": detail,
            "request_id": f"req_{uuid4().hex}",
            "errors": errors,
        },
    )
