import asyncio
import socket
import uuid
from collections.abc import AsyncIterator
from typing import ClassVar

import pytest
import socketio
import uvicorn
from httpx import AsyncClient

from app.core.config import Settings
from app.core.mail import EmailSender, OutboxEmailSender
from app.core.realtime import SOCKETIO_PATH, Event, RealtimePublisher
from app.main import create_app
from tests.helpers import register_verified


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


@pytest.fixture
async def live(
    settings: Settings,
) -> AsyncIterator[tuple[str, OutboxEmailSender, RealtimePublisher]]:
    """Real HTTP + WebSocket server (Socket.IO cannot run over the in-memory ASGI transport).

    Yields the base URL, the server's own outbox (to verify accounts) and its publisher.
    """
    app = create_app(settings)
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    task = asyncio.create_task(server.serve())
    while not server.started:  # noqa: ASYNC110 -- uvicorn exposes a flag, not an event
        await asyncio.sleep(0.02)
    sender = await app.state.dishka_container.get(EmailSender)
    assert isinstance(sender, OutboxEmailSender)
    publisher = await app.state.dishka_container.get(RealtimePublisher)
    yield f"http://127.0.0.1:{port}", sender, publisher
    server.should_exit = True
    await task


class Ping(Event):
    event_name: ClassVar[str] = "test.ping"

    message_text: str


async def test_events_reach_all_devices_of_the_user_only(
    live: tuple[str, OutboxEmailSender, RealtimePublisher],
) -> None:
    live_url, outbox, publisher = live
    async with AsyncClient(base_url=live_url) as http:
        owner = (await register_verified(http, outbox, "owner@example.com", prefix="/api/v1"))[
            "accessToken"
        ]
        stranger = (
            await register_verified(http, outbox, "stranger@example.com", prefix="/api/v1")
        )["accessToken"]
        me = await http.get("/api/v1/users/me", headers={"Authorization": f"Bearer {owner}"})
        owner_id = uuid.UUID(me.json()["id"])

        async with (
            socketio.AsyncSimpleClient() as phone,
            socketio.AsyncSimpleClient() as laptop,
            socketio.AsyncSimpleClient() as other,
        ):
            for client, token in ((phone, owner), (laptop, owner), (other, stranger)):
                await client.connect(
                    live_url,
                    socketio_path=SOCKETIO_PATH,
                    auth={"token": token},
                    transports=["websocket"],
                )

            await publisher.to_user(owner_id, Ping(message_text="hello"))

            for device in (phone, laptop):
                name, payload = await device.receive(timeout=5)
                assert name == "test.ping"
                assert payload == {"messageText": "hello"}  # camelCase payload, like HTTP

            with pytest.raises(socketio.exceptions.TimeoutError):
                await other.receive(timeout=0.5)


async def test_connection_requires_valid_token(
    live: tuple[str, OutboxEmailSender, RealtimePublisher],
) -> None:
    live_url, _, _ = live
    client = socketio.AsyncSimpleClient()
    with pytest.raises(socketio.exceptions.ConnectionError):
        await client.connect(
            live_url,
            socketio_path=SOCKETIO_PATH,
            auth={"token": "invalid"},
            transports=["websocket"],
        )
