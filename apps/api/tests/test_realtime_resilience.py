"""A broken realtime transport must never turn a committed write into a 500."""

import uuid
from typing import ClassVar

from app.core.realtime import Event, RealtimePublisher


class Ping(Event):
    event_name: ClassVar[str] = "test.ping"


class ExplodingServer:
    async def emit(self, *args: object, **kwargs: object) -> None:
        raise RuntimeError("redis is down")


async def test_publish_failure_is_swallowed_and_logged() -> None:
    publisher = RealtimePublisher(ExplodingServer())  # type: ignore[arg-type]

    await publisher.to_user(uuid.uuid4(), Ping())
