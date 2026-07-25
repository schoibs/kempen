from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from api.errors import ApiProblem, problem_handler, validation_problem_handler
from api.routes.assets import router as assets_router
from api.routes.health import router as health_router
from app_config import get_settings
from logging_config import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(level=settings.log_level)

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
    )
    application.add_exception_handler(ApiProblem, problem_handler)
    application.add_exception_handler(RequestValidationError, validation_problem_handler)
    application.include_router(assets_router)
    application.include_router(health_router)
    return application


app = create_app()
