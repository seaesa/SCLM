"""Accountants split the partners; a contract and its addenda belong to the partner's owner."""

from io import BytesIO

from dishka import AsyncContainer
from httpx import AsyncClient
from openpyxl import load_workbook

from app.core.mail import OutboxEmailSender
from app.shared.permissions import Role
from tests.contract_factory import (
    CONTRACT_FACTS,
    add_document,
    enter,
    grant,
    maker,
    new_contract,
)
from tests.helpers import register_verified

__all__ = ["maker"]

_PRICE_ADDENDUM = {
    "number": "PL01",
    "signed_on": "2023-03-01",
    "effective_from": "2023-03-01",
    "adjustments": "price,fuel",
}


async def test_contracts_and_addenda_follow_the_partner_owner(
    auth_client: AsyncClient, container: AsyncContainer
) -> None:
    await grant(container, "jane@example.com", Role.ADMIN)
    me = (await auth_client.get("/users/me")).json()
    contract = await new_contract(auth_client, container)
    await enter(auth_client, contract["instruments"][0]["id"], CONTRACT_FACTS)
    await add_document(auth_client, contract, "addendum", _PRICE_ADDENDUM)

    unassigned = await auth_client.get("/contracts", params={"isUnassigned": True})
    assigned = await auth_client.put(
        "/partners/owner", json={"partnerIds": [contract["partnerId"]], "ownerId": me["id"]}
    )
    mine = await auth_client.get("/contracts", params={"ownerId": me["id"]})
    addenda = await auth_client.get(
        "/contract-instruments", params={"ownerId": me["id"], "adjustment": "fuel"}
    )
    export = await auth_client.get("/contract-instruments/export", params={"ownerId": me["id"]})

    assert unassigned.json()["total"] == 1
    assert assigned.status_code == 204
    assert mine.json()["items"][0]["owner"]["id"] == me["id"]
    [addendum] = addenda.json()["items"]
    assert addendum["code"].endswith("-PL01")
    assert addendum["adjustments"] == ["price", "fuel"]
    assert addendum["effectiveFrom"] == "2023-03-01"
    assert addendum["owner"]["id"] == me["id"]
    rows = list(load_workbook(BytesIO(export.content)).active.iter_rows(values_only=True))
    assert len(rows) == 2
    assert rows[1][2] == addendum["code"]


async def test_only_someone_who_handles_contracts_can_own_partners(
    auth_client: AsyncClient,
    client: AsyncClient,
    outbox: OutboxEmailSender,
    container: AsyncContainer,
) -> None:
    await grant(container, "jane@example.com", Role.ADMIN)
    await register_verified(client, outbox, "dan@example.com")
    await grant(container, "dan@example.com", Role.DIRECTOR)
    contract = await new_contract(auth_client, container)
    dan = (await auth_client.get("/users", params={"q": "dan@"})).json()["items"][0]

    refused = await auth_client.put(
        "/partners/owner", json={"partnerIds": [contract["partnerId"]], "ownerId": dan["id"]}
    )

    assert refused.status_code == 409
    assert refused.json()["code"] == "owner_cannot_handle_contracts"


async def test_accountants_assign_owners_and_directors_cannot(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    created = await new_contract(maker, container)
    me = (await maker.get("/users/me")).json()
    body = {"partnerIds": [created["partnerId"]], "ownerId": me["id"]}

    candidates = (await maker.get("/partners/owner-candidates")).json()
    assert me["id"] in [c["id"] for c in candidates]
    assert (await maker.put("/partners/owner", json=body)).status_code == 204
    owned = (await maker.get("/contracts", params={"ownerId": me["id"]})).json()
    assert owned["total"] == 1

    await grant(container, "jane@example.com", Role.DIRECTOR)
    assert (await maker.put("/partners/owner", json=body)).status_code == 403


async def test_contracts_filter_by_any_of_several_categories(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    await new_contract(maker, container)

    customers = await maker.get("/contracts", params={"categories": ["customer", "warehouse"]})
    contractors = await maker.get("/contracts", params={"categories": ["contractor"]})

    assert customers.json()["total"] == 1
    assert contractors.json()["total"] == 0
