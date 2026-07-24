from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from redis import Redis
from sqlalchemy import text

from app_config import get_settings
from persistence.database import get_engine


PROJECT_ROOT = Path(__file__).resolve().parent


class MigrationStateError(RuntimeError):
    """Raised when the database is not at the expected Alembic revision."""


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    return Redis.from_url(
        get_settings().redis_url,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def check_database_and_migrations() -> None:
    alembic_config = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_config.set_main_option(
        "script_location",
        str(PROJECT_ROOT / "persistence" / "migrations"),
    )
    expected_heads = set(ScriptDirectory.from_config(alembic_config).get_heads())

    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
        current_heads = set(
            MigrationContext.configure(connection).get_current_heads()
        )

    if current_heads != expected_heads:
        raise MigrationStateError(
            "Database migration revision does not match the application head."
        )


def check_redis() -> None:
    if not get_redis_client().ping():
        raise ConnectionError("Redis ping did not return success.")
