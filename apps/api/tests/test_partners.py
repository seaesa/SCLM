"""Partners come from the source of record (ADR 0006): a sync never merges, deletes or guesses;
anything a person must decide becomes a conflict."""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from dishka import AsyncContainer
from httpx import AsyncClient

from app.modules.partners.source import (
    DuplicateCodeError,
    JsonFilePartnerSource,
)
from app.modules.users.service import UserService
from app.shared.permissions import Role
from tests.partner_factory import FakeSource, partner, sync


async def _grant(container: AsyncContainer, *roles: Role) -> None:
    async with container() as request:
        users = await request.get(UserService)
        user = await users.get_by_email("jane@example.com")
        assert user is not None
        await users.set_roles(user, roles)


async def _open_conflicts(client: AsyncClient) -> list[dict[str, object]]:
    response = await client.get("/partner-conflicts", params={"isOpen": True})
    assert response.status_code == 200, response.text
    items: list[dict[str, object]] = response.json()["items"]
    return items


def test_json_source_merges_a_code_listed_as_customer_and_supplier(tmp_path: Path) -> None:
    customers = tmp_path / "customers.json"
    suppliers = tmp_path / "suppliers.json"
    customers.write_text(
        json.dumps([{"code": "KH1", "company_name": "Alpha", "tax_code": "0101", "address": "A"}])
    )
    suppliers.write_text(
        json.dumps([{"code": "KH1", "name": "KH1 Alpha", "tax_code": "", "address": "B"}])
    )

    [partner] = JsonFilePartnerSource([customers], [suppliers]).fetch()

    assert partner.is_customer
    assert partner.is_supplier
    assert partner.tax_code == "0101"  # empty on one side is filled from the other
    assert partner.address == "A"
    assert partner.mismatches == {"address": ["A", "B"]}


def test_json_source_rejects_a_code_repeated_in_one_side(tmp_path: Path) -> None:
    customers = tmp_path / "customers.json"
    customers.write_text(json.dumps([{"code": "KH1", "name": "A"}, {"code": "KH1", "name": "B"}]))

    with pytest.raises(DuplicateCodeError):
        JsonFilePartnerSource([customers], []).fetch()


async def test_sync_is_idempotent_and_reports_changes(container: AsyncContainer) -> None:
    source = FakeSource(partner("KH1", "Alpha"), partner("KH2", "Beta"))
    first = await sync(container, source)
    assert (first.created, first.updated, first.unchanged) == (2, 0, 0)

    assert (await sync(container, source)).unchanged == 2

    source.records = [partner("KH1", "Alpha 2"), partner("KH2", "Beta")]
    again = await sync(container, source)
    assert (again.created, again.updated, again.unchanged) == (0, 1, 1)


async def test_shared_tax_code_is_a_conflict_not_a_merge(
    auth_client: AsyncClient, container: AsyncContainer
) -> None:
    await _grant(container, Role.ADMIN)
    report = await sync(
        container,
        FakeSource(partner("KH1", "Alpha HN", "0101"), partner("KH2", "Alpha HCM", "0101")),
    )
    assert report.created == 2
    assert report.conflicts_open == 2

    conflicts = await _open_conflicts(auth_client)
    assert {c["kind"] for c in conflicts} == {"duplicate_tax_code"}

    listed = (await auth_client.get("/partners", params={"q": "0101"})).json()["items"]
    assert sorted(p["code"] for p in listed) == ["KH1", "KH2"]


async def test_conflicts_close_when_the_source_is_fixed(
    auth_client: AsyncClient, container: AsyncContainer
) -> None:
    await _grant(container, Role.ADMIN)
    mismatch = partner("KH1", "Alpha", mismatches={"name": ["Alpha", "Alfa"]})
    source = FakeSource(mismatch, partner("KH2", "Beta"))
    await sync(container, source)

    source.records = [partner("KH1", "Alpha")]
    report = await sync(container, source)

    kinds = {c["kind"] for c in await _open_conflicts(auth_client)}
    assert kinds == {"missing_from_source"}  # KH2 is kept, never deleted
    assert report.conflicts_closed == 1


async def test_acknowledged_conflict_stays_closed_until_it_changes(
    auth_client: AsyncClient, container: AsyncContainer
) -> None:
    await _grant(container, Role.ADMIN)
    source = FakeSource(partner("KH1", "A", "0101"), partner("KH2", "B", "0101"))
    await sync(container, source)
    for conflict in await _open_conflicts(auth_client):
        response = await auth_client.post(
            f"/partner-conflicts/{conflict['id']}/resolve", json={"note": "two branches"}
        )
        assert response.status_code == 204

    assert (await sync(container, source)).conflicts_opened == 0

    source.records = [*source.records, partner("KH3", "C", "0101")]
    assert (await sync(container, source)).conflicts_opened == 3


async def test_resolving_twice_is_a_conflict(
    auth_client: AsyncClient, container: AsyncContainer
) -> None:
    await _grant(container, Role.ADMIN)
    await sync(container, FakeSource(partner("KH1", "A", "0101"), partner("KH2", "B", "0101")))
    conflict_id = (await _open_conflicts(auth_client))[0]["id"]
    url = f"/partner-conflicts/{conflict_id}/resolve"

    assert (await auth_client.post(url, json={"note": "ok"})).status_code == 204
    second = await auth_client.post(url, json={"note": "ok"})
    assert second.status_code == 409


async def test_partner_access_needs_permission(
    auth_client: AsyncClient, container: AsyncContainer
) -> None:
    assert (await auth_client.get("/partners")).status_code == 403

    await _grant(container, Role.ACCOUNTANT)
    assert (await auth_client.get("/partners")).status_code == 200
    assert (await auth_client.get("/partner-conflicts")).status_code == 403


async def test_search_matches_code_and_name(
    auth_client: AsyncClient, container: AsyncContainer
) -> None:
    await _grant(container, Role.ACCOUNTANT)
    await sync(
        container,
        FakeSource(partner("KH0001", "Masan Consumer"), replace(partner("NCC9", "Bee Chain"))),
    )

    def codes(response_json: dict[str, list[dict[str, str]]]) -> list[str]:
        return [p["code"] for p in response_json["items"]]

    assert codes((await auth_client.get("/partners", params={"q": "masan"})).json()) == ["KH0001"]
    assert codes((await auth_client.get("/partners", params={"q": "ncc9"})).json()) == ["NCC9"]
