from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Request
from redis import Redis
from redis.exceptions import RedisError

from api.dependencies import Principal
from api.errors import ApiProblem
from app_config import get_settings
from infrastructure import get_redis_client


def enforce_request_limit(*, request: Request, redis: Redis | None = None) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled or request.url.path.startswith("/health/"):
        return
    identifier = request.client.host if request.client else "unknown"
    window = int(datetime.now(UTC).timestamp()) // settings.rate_limit_window_sec
    key = f"campaign:rate:{identifier}:{window}"
    client = redis or get_redis_client()
    try:
        count = int(client.incr(key))
    except RedisError as exc:
        raise ApiProblem(
            status=503,
            code="SERVICE_UNAVAILABLE",
            title="Rate-limit service unavailable",
            detail="Request admission is temporarily unavailable.",
        ) from exc
    if count == 1:
        client.expire(key, settings.rate_limit_window_sec + 1)
    if count > settings.rate_limit_requests:
        raise ApiProblem(
            status=429,
            code="RATE_LIMITED",
            title="Too many requests",
            detail="Request rate exceeded. Retry after the current rate window.",
        )


def reserve_campaign_quota(*, principal: Principal, campaign_id: str, redis: Redis | None = None) -> bool:
    settings = get_settings()
    client = redis or get_redis_client()
    active_key = f"campaign:active:{principal.tenant_id}"
    daily_key = f"campaign:daily:{principal.tenant_id}:{datetime.now(UTC):%Y-%m-%d}"
    try:
        added = bool(client.sadd(active_key, campaign_id))
    except RedisError as exc:
        raise ApiProblem(
            status=503,
            code="SERVICE_UNAVAILABLE",
            title="Quota service unavailable",
            detail="Campaign admission is temporarily unavailable.",
        ) from exc
    if not added:
        return False
    client.expire(active_key, settings.artifact_retention_sec)
    daily_count = int(client.incr(daily_key))
    if daily_count == 1:
        client.expire(daily_key, 2 * 24 * 60 * 60)
    active_count = int(client.scard(active_key))
    if active_count > settings.tenant_concurrent_campaign_quota:
        client.srem(active_key, campaign_id)
        client.decr(daily_key)
        raise ApiProblem(
            status=429,
            code="CONCURRENT_QUOTA_EXCEEDED",
            title="Concurrent campaign quota exceeded",
            detail="Wait for an in-progress campaign to finish before submitting another.",
        )
    if daily_count > settings.tenant_daily_campaign_quota:
        client.srem(active_key, campaign_id)
        client.decr(daily_key)
        raise ApiProblem(
            status=429,
            code="DAILY_QUOTA_EXCEEDED",
            title="Daily campaign quota exceeded",
            detail="The tenant daily campaign limit has been reached.",
        )
    return True


def release_campaign_quota(*, tenant_id: str, campaign_id: str, redis: Redis | None = None) -> None:
    client = redis or get_redis_client()
    client.srem(f"campaign:active:{tenant_id}", campaign_id)
