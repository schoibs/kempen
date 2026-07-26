from __future__ import annotations

from celery import Celery
from kombu import Queue

from app_config import get_settings


settings = get_settings()

celery_app = Celery(
    "campaign_generator",
    broker=settings.redis_url,
    include=["workers.tasks", "workers.maintenance"],
)
celery_app.conf.update(
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    enable_utc=True,
    result_backend=None,
    task_acks_late=True,
    task_default_queue="planning",
    task_queues=(
        Queue("planning", routing_key="planning"),
        Queue("media", routing_key="media"),
    ),
    task_ignore_result=True,
    task_routes={
        "campaign.run_stage": {"queue": "planning"},
        "campaign.cleanup_storage": {"queue": "planning"},
        "campaign.configure_storage_lifecycle": {"queue": "planning"},
    },
    task_reject_on_worker_lost=True,
    task_serializer="json",
    timezone="UTC",
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    task_soft_time_limit=60 * 60,
    task_time_limit=60 * 60 + 60,
)
