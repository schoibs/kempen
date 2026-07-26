from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from api.errors import ApiProblem
from api.limits import enforce_request_limit
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        try:
            enforce_request_limit(request=request)
            return await call_next(request)
        except ApiProblem as error:
            return JSONResponse(
                status_code=error.status,
                content={
                    "type": f"https://api.example.com/problems/{error.code.lower().replace('_', '-')}",
                    "title": error.title,
                    "status": error.status,
                    "code": error.code,
                    "detail": error.detail,
                    "errors": [],
                },
            )
