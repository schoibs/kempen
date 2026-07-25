from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from domain.enums import CampaignStage
from storage import ObjectStorageError


@dataclass(frozen=True)
class StageFailure:
    """A sanitized, persistence-safe classification for a failed stage."""

    code: str
    message: str
    retryable: bool


class ProviderStageError(RuntimeError):
    """An operation can raise an already-classified provider failure."""

    def __init__(self, *, code: str, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.failure = StageFailure(code=code, message=message, retryable=retryable)


def classify_stage_failure(*, error: Exception, stage: CampaignStage) -> StageFailure:
    """Map provider and transfer failures without exposing provider payloads."""

    if isinstance(error, ProviderStageError):
        return error.failure
    if isinstance(error, ObjectStorageError):
        if stage in {CampaignStage.STORYBOARD_GENERATION, CampaignStage.VIDEO_FINALIZE}:
            return StageFailure(
                code="ARTIFACT_UPLOAD_FAILED",
                message="Campaign artifact storage is temporarily unavailable.",
                retryable=True,
            )
        return StageFailure(
            code="PROVIDER_UNAVAILABLE",
            message="Campaign input storage is temporarily unavailable.",
            retryable=True,
        )

    chain = tuple(_exception_chain(error))
    status_code = next(
        (code for item in chain if (code := _status_code(item)) is not None),
        None,
    )
    names = " ".join(type(item).__name__.lower() for item in chain)
    messages = " ".join(str(item).lower() for item in chain)

    if status_code in {401, 403} or any(
        marker in messages for marker in ("api key", "authentication", "unauthorized", "forbidden")
    ):
        return StageFailure(
            code="PROVIDER_AUTH_ERROR",
            message="A campaign generation provider could not authenticate.",
            retryable=False,
        )
    if status_code == 429 or "ratelimit" in names or "rate limit" in messages:
        return StageFailure(
            code="PROVIDER_RATE_LIMITED",
            message="A campaign generation provider is temporarily rate limited.",
            retryable=True,
        )
    if "content policy" in messages or "content_filter" in messages or "safety" in messages:
        return StageFailure(
            code="PROVIDER_CONTENT_POLICY",
            message="A campaign generation provider rejected the requested content.",
            retryable=False,
        )
    if _is_timeout(status_code=status_code, names=names, messages=messages):
        if stage in {
            CampaignStage.PRODUCT_ANALYSIS,
            CampaignStage.NARRATIVE_STRATEGY,
            CampaignStage.STORYBOARD_GENERATION,
            CampaignStage.VIDEO_SUBMISSION,
        }:
            return StageFailure(
                code="PROVIDER_TIMEOUT_AMBIGUOUS",
                message="A provider request timed out after it may have been accepted.",
                retryable=True,
            )
        return StageFailure(
            code="ARTIFACT_DOWNLOAD_FAILED"
            if stage == CampaignStage.VIDEO_FINALIZE
            else "PROVIDER_UNAVAILABLE",
            message="A provider request timed out before it could be completed.",
            retryable=True,
        )
    if (
        (status_code is not None and status_code >= 500)
        or _is_connection_failure(names, messages)
    ):
        return StageFailure(
            code="PROVIDER_UNAVAILABLE",
            message="A campaign generation provider is temporarily unavailable.",
            retryable=True,
        )
    if stage == CampaignStage.VIDEO_FINALIZE:
        return StageFailure(
            code="ARTIFACT_DOWNLOAD_FAILED",
            message="The generated video could not be downloaded.",
            retryable=True,
        )
    return StageFailure(
        code="PROVIDER_BAD_RESPONSE",
        message="A campaign generation provider returned an unusable response.",
        retryable=False,
    )


def _exception_chain(error: Exception) -> Iterable[BaseException]:
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def _status_code(error: BaseException) -> int | None:
    direct = getattr(error, "status_code", None)
    if isinstance(direct, int):
        return direct
    response = getattr(error, "response", None)
    nested = getattr(response, "status_code", None)
    return nested if isinstance(nested, int) else None


def _is_timeout(*, status_code: int | None, names: str, messages: str) -> bool:
    return status_code == 408 or "timeout" in names or "timed out" in messages


def _is_connection_failure(names: str, messages: str) -> bool:
    markers = ("connection", "network", "unavailable", "temporarily")
    return any(marker in names or marker in messages for marker in markers)
