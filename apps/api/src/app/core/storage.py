"""Immutable, content-addressed file storage on an S3-compatible bucket (ADR 0005)."""

import asyncio
import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol
from urllib.parse import quote

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import Settings

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


@dataclass(frozen=True)
class StoredObject:
    key: str
    sha256: str
    size: int
    # False when the same bytes were already stored: nothing was written.
    is_new: bool


def object_key(sha256: str) -> str:
    return f"sha256/{sha256}"


class ObjectStorage(Protocol):
    async def put(self, data: bytes, content_type: str) -> StoredObject:
        """Store `data` under its SHA-256. Storing the same bytes again writes nothing."""
        ...

    async def get(self, key: str) -> bytes: ...

    async def download_url(self, key: str, filename: str) -> str:
        """A short-lived URL a browser can open; give it only after a permission check."""
        ...


def _client(settings: Settings, endpoint_url: str) -> "S3Client":
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.storage_access_key,
        aws_secret_access_key=settings.storage_secret_key.get_secret_value(),
        region_name=settings.storage_region,
        # RustFS/MinIO serve buckets as a path, not as a subdomain.
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


class S3ObjectStorage:
    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.storage_bucket
        self._url_seconds = settings.storage_download_url_seconds
        self._client = _client(settings, settings.storage_endpoint_url)
        # A presigned URL is signed for its host, so links for browsers are signed against the
        # address they can reach, which differs from the API's when both run in containers.
        self._signer = _client(
            settings, settings.storage_public_url or settings.storage_endpoint_url
        )
        self._cors_origins = settings.cors_origins
        self._bucket_ready = False

    async def _ensure_bucket(self) -> None:
        if self._bucket_ready:
            return
        try:
            await asyncio.to_thread(self._client.head_bucket, Bucket=self._bucket)
        except ClientError:
            await asyncio.to_thread(self._client.create_bucket, Bucket=self._bucket)
        # The web PDF viewer fetches files by script (with Range requests), which the browser
        # allows only when the bucket answers CORS for the web origins.
        await asyncio.to_thread(
            self._client.put_bucket_cors,
            Bucket=self._bucket,
            CORSConfiguration={
                "CORSRules": [
                    {
                        "AllowedOrigins": self._cors_origins,
                        "AllowedMethods": ["GET", "HEAD"],
                        "AllowedHeaders": ["*"],
                        "ExposeHeaders": ["Content-Length", "Content-Range", "Accept-Ranges"],
                        "MaxAgeSeconds": 3600,
                    }
                ]
            },
        )
        self._bucket_ready = True

    async def _exists(self, key: str) -> bool:
        try:
            await asyncio.to_thread(self._client.head_object, Bucket=self._bucket, Key=key)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise
        return True

    async def put(self, data: bytes, content_type: str) -> StoredObject:
        await self._ensure_bucket()
        sha256 = hashlib.sha256(data).hexdigest()
        key = object_key(sha256)
        # Never overwrite: an existing key already holds exactly these bytes.
        if await self._exists(key):
            return StoredObject(key=key, sha256=sha256, size=len(data), is_new=False)
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return StoredObject(key=key, sha256=sha256, size=len(data), is_new=True)

    async def get(self, key: str) -> bytes:
        response = await asyncio.to_thread(self._client.get_object, Bucket=self._bucket, Key=key)
        return await asyncio.to_thread(response["Body"].read)

    async def download_url(self, key: str, filename: str) -> str:
        await self._ensure_bucket()
        return self._signer.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self._bucket,
                "Key": key,
                "ResponseContentDisposition": f"inline; filename*=UTF-8''{quote(filename)}",
            },
            ExpiresIn=self._url_seconds,
        )
