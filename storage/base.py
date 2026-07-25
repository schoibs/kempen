from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


class ObjectStorageError(RuntimeError):
    """Raised when object storage cannot complete an operation."""


class ObjectNotFoundError(ObjectStorageError):
    """Raised when an expected private object does not exist."""


@dataclass(frozen=True)
class PresignedUpload:
    url: str
    headers: dict[str, str]


@dataclass(frozen=True)
class ObjectMetadata:
    content_type: str | None
    size_bytes: int
    checksum_sha256: str | None


class ObjectStorage(ABC):
    """The small object-storage contract used by API routes and workers."""

    @abstractmethod
    def ensure_bucket(self) -> None:
        """Ensure the configured private bucket is available."""

    @abstractmethod
    def create_upload_url(
        self,
        *,
        object_key: str,
        content_type: str,
        expires_in_sec: int,
        checksum_sha256: str | None,
    ) -> PresignedUpload:
        """Create a direct PUT URL with the expected upload metadata."""

    @abstractmethod
    def head_object(self, *, object_key: str) -> ObjectMetadata:
        """Return verified metadata for an existing private object."""

    @abstractmethod
    def create_download_url(self, *, object_key: str, expires_in_sec: int) -> str:
        """Create a temporary private GET URL."""

    @abstractmethod
    def download_bytes(self, *, object_key: str, max_bytes: int) -> bytes:
        """Download a bounded object for worker-side validation."""

    @abstractmethod
    def upload_file(
        self,
        *,
        object_key: str,
        local_path: str | Path,
        content_type: str,
    ) -> ObjectMetadata:
        """Upload a generated artifact and return its stored metadata."""

    @abstractmethod
    def delete_object(self, *, object_key: str) -> None:
        """Remove a failed or quarantined upload."""
