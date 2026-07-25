from __future__ import annotations

from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


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
