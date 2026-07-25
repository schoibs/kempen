from __future__ import annotations

import base64

from functools import lru_cache
from typing import Any

import boto3

from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError

from app_config import get_settings

from .base import (
    ObjectMetadata,
    ObjectNotFoundError,
    ObjectStorage,
    ObjectStorageError,
    PresignedUpload,
)


class S3ObjectStorage(ObjectStorage):
    """Private S3-compatible storage backed by boto3, including MinIO."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        region_name: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        client: Any | None = None,
    ) -> None:
        self.bucket = bucket
        self.region_name = region_name
        self._client = client or boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region_name,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self.bucket)
            return
        except ClientError as exc:
            if self._error_code(exc) not in {"404", "NoSuchBucket", "NotFound"}:
                raise ObjectStorageError("Could not access the configured object bucket.") from exc

        try:
            create_args: dict[str, Any] = {"Bucket": self.bucket}
            if self.region_name != "us-east-1":
                create_args["CreateBucketConfiguration"] = {
                    "LocationConstraint": self.region_name,
                }
            self._client.create_bucket(**create_args)
        except (ClientError, BotoCoreError) as exc:
            raise ObjectStorageError("Could not create the configured object bucket.") from exc

    def create_upload_url(
        self,
        *,
        object_key: str,
        content_type: str,
        expires_in_sec: int,
        checksum_sha256: str | None,
    ) -> PresignedUpload:
        parameters: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": object_key,
            "ContentType": content_type,
        }
        headers = {"Content-Type": content_type}
        if checksum_sha256:
            checksum_base64 = _sha256_hex_to_base64(checksum_sha256)
            parameters["ChecksumSHA256"] = checksum_base64
            headers["x-amz-checksum-sha256"] = checksum_base64
        try:
            url = self._client.generate_presigned_url(
                "put_object",
                Params=parameters,
                ExpiresIn=expires_in_sec,
                HttpMethod="PUT",
            )
        except (ClientError, BotoCoreError) as exc:
            raise ObjectStorageError("Could not create an upload URL.") from exc
        return PresignedUpload(url=url, headers=headers)

    def head_object(self, *, object_key: str) -> ObjectMetadata:
        try:
            response = self._client.head_object(Bucket=self.bucket, Key=object_key)
        except ClientError as exc:
            if self._error_code(exc) in {"404", "NoSuchKey", "NotFound"}:
                raise ObjectNotFoundError("Object not found.") from exc
            raise ObjectStorageError("Could not inspect uploaded object.") from exc
        except BotoCoreError as exc:
            raise ObjectStorageError("Could not inspect uploaded object.") from exc
        return ObjectMetadata(
            content_type=response.get("ContentType"),
            size_bytes=int(response["ContentLength"]),
            checksum_sha256=response.get("ChecksumSHA256"),
        )

    def create_download_url(self, *, object_key: str, expires_in_sec: int) -> str:
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": object_key},
                ExpiresIn=expires_in_sec,
                HttpMethod="GET",
            )
        except (ClientError, BotoCoreError) as exc:
            raise ObjectStorageError("Could not create a download URL.") from exc

    def download_bytes(self, *, object_key: str, max_bytes: int) -> bytes:
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=object_key)
        except ClientError as exc:
            if self._error_code(exc) in {"404", "NoSuchKey", "NotFound"}:
                raise ObjectNotFoundError("Object not found.") from exc
            raise ObjectStorageError("Could not download object.") from exc
        except BotoCoreError as exc:
            raise ObjectStorageError("Could not download object.") from exc

        body = response["Body"]
        chunks: list[bytes] = []
        total_bytes = 0
        try:
            for chunk in body.iter_chunks(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise ObjectStorageError("Object exceeds the configured size limit.")
                chunks.append(chunk)
        finally:
            body.close()
        return b"".join(chunks)

    def delete_object(self, *, object_key: str) -> None:
        try:
            self._client.delete_object(Bucket=self.bucket, Key=object_key)
        except (ClientError, BotoCoreError) as exc:
            raise ObjectStorageError("Could not remove object.") from exc

    @staticmethod
    def _error_code(error: ClientError) -> str:
        return str(error.response.get("Error", {}).get("Code", ""))


@lru_cache(maxsize=1)
def get_object_storage() -> S3ObjectStorage:
    settings = get_settings()
    return S3ObjectStorage(
        endpoint_url=settings.object_storage_endpoint,
        region_name=settings.object_storage_region,
        bucket=settings.object_storage_bucket,
        access_key=settings.object_storage_access_key.get_secret_value(),
        secret_key=settings.object_storage_secret_key.get_secret_value(),
    )


def _sha256_hex_to_base64(value: str) -> str:
    try:
        return base64.b64encode(bytes.fromhex(value)).decode("ascii")
    except ValueError as exc:
        raise ValueError("sha256 must be lowercase hexadecimal.") from exc
