"""Contracts with entered facts, for tests that need one."""

from typing import Any

import pytest
from dishka import AsyncContainer
from httpx import AsyncClient, Response

from app.modules.users.service import UserService
from app.shared.permissions import Role
from tests.partner_factory import FakeSource, partner, sync


async def grant(container: AsyncContainer, email: str, *roles: Role) -> None:
    async with container() as request:
        users = await request.get(UserService)
        user = await users.get_by_email(email)
        assert user is not None
        await users.set_roles(user, roles)


@pytest.fixture
async def maker(auth_client: AsyncClient, container: AsyncContainer) -> AsyncClient:
    """Jane records contracts."""
    await grant(container, "jane@example.com", Role.ACCOUNTANT)
    return auth_client


async def post_contract(
    client: AsyncClient,
    partner_id: str,
    filename: str = "contract.pdf",
    **form: str,
) -> Response:
    """Create a contract with its contract document from one uploaded scan."""
    return await client.post(
        "/contracts",
        data={"category": "customer", "partnerId": partner_id, **form},
        files={"file": (filename, f"%PDF {filename}".encode(), "application/pdf")},
    )


async def new_contract(
    client: AsyncClient, container: AsyncContainer, **form: str
) -> dict[str, Any]:
    """A contract for customer KH1 with its contract document (signed unless `needsApproval`)."""
    await sync(container, FakeSource(partner("KH1", "Masan")))
    partner_id = (await client.get("/partners", params={"q": "KH1"})).json()["items"][0]["id"]
    response = await post_contract(client, partner_id, **form)
    assert response.status_code == 201, response.text
    detail = response.json()
    return {**detail, "fileId": detail["instruments"][0]["fileId"], "partnerId": partner_id}


CONTRACT_FACTS = {
    "number": "2022/MSC-SPIDER/VC",
    "signed_on": "2022-03-15",
    "effective_from": "2022-03-15",
    "expires_on": "2023-03-14",
    "renewal": "none",
}


async def enter(client: AsyncClient, instrument_id: str, facts: dict[str, str]) -> None:
    response = await client.put(
        f"/contract-instruments/{instrument_id}/facts", json={"values": facts}
    )
    assert response.status_code == 200, response.text


async def add_document(
    client: AsyncClient, contract: dict[str, Any], kind: str, facts: dict[str, str]
) -> str:
    """Record one more document of `contract` and enter its facts; returns its id."""
    before = await client.get(f"/contracts/{contract['id']}")
    known = {i["id"] for i in before.json()["instruments"]}
    response = await client.post(
        f"/contracts/{contract['id']}/instruments",
        json={"kind": kind, "fileId": contract["fileId"]},
    )
    assert response.status_code == 201, response.text
    # The detail lists documents by date, so the new one is found by its id.
    [instrument_id] = [i["id"] for i in response.json()["instruments"] if i["id"] not in known]
    await enter(client, instrument_id, facts)
    return instrument_id
