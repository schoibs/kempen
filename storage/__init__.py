"""Private object-storage interfaces and implementations."""

from .base import (
    ObjectMetadata,
    ObjectNotFoundError,
    ObjectStorage,
    ObjectStorageError,
    PresignedUpload,
)
from .s3 import S3ObjectStorage, get_object_storage

__all__ = [
    "ObjectMetadata",
    "ObjectNotFoundError",
    "ObjectStorage",
    "ObjectStorageError",
    "PresignedUpload",
    "S3ObjectStorage",
    "get_object_storage",
]
