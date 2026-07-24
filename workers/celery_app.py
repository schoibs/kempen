from __future__ import annotations

from celery import Celery

from app_config import get_settings


settings = get_settings()

celery_app = Celery(
    "campaign_generator",
    broker=settings.redis_url,
    include=["workers.tasks"],
)
celery_app.conf.update(
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    enable_utc=True,
    result_backend=None,
    task_acks_late=True,
    task_default_queue="planning",
    task_ignore_result=True,
    task_reject_on_worker_lost=True,
    task_serializer="json",
    timezone="UTC",
    worker_prefetch_multiplier=1,
)
