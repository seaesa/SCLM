"""Contract files are immutable and content-addressed (ADR 0005), against the real RustFS."""

import hashlib
import uuid

import httpx
from dishka import AsyncContainer

from app.core.config import Settings
from app.core.storage import ObjectStorage, S3ObjectStorage


async def test_same_bytes_are_stored_once(container: AsyncContainer) -> None:
    storage = await container.get(ObjectStorage)
    data = f"signed contract {uuid.uuid4()}".encode()

    first = await storage.put(data, "application/pdf")
    again = await storage.put(data, "application/pdf")

    assert first.key == f"sha256/{hashlib.sha256(data).hexdigest()}"
    assert first.is_new
    assert not again.is_new
    assert again.key == first.key
    assert await storage.get(first.key) == data


async def test_download_url_serves_the_file(container: AsyncContainer) -> None:
    storage = await container.get(ObjectStorage)
    data = f"addendum {uuid.uuid4()}".encode()
    stored = await storage.put(data, "application/pdf")

    url = await storage.download_url(stored.key, "contract é.pdf")
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    assert response.status_code == 200
    assert response.content == data
    assert "filename*=UTF-8''contract%20%C3%A9.pdf" in response.headers["content-disposition"]


async def test_download_url_is_signed_for_the_public_address(container: AsyncContainer) -> None:
    settings = (await container.get(Settings)).model_copy(
        update={"storage_public_url": "http://files.example.test:9100"}
    )
    url = await S3ObjectStorage(settings).download_url("sha256/abc", "a.pdf")

    assert url.startswith("http://files.example.test:9100/")


async def test_the_bucket_answers_cors_for_the_web_origins(container: AsyncContainer) -> None:
    settings = await container.get(Settings)
    storage = S3ObjectStorage(settings)
    stored = await storage.put(b"%PDF-1.4 cors", "application/pdf")
    url = await storage.download_url(stored.key, "a.pdf")

    origin = settings.cors_origins[0]
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers={"Origin": origin, "Range": "bytes=0-3"})

    assert response.headers["access-control-allow-origin"] == origin
