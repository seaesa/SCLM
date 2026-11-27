"""Re-signing a contract, the renewal filter and contracts that overlap."""

from dishka import AsyncContainer
from httpx import AsyncClient, Response

from tests.contract_factory import CONTRACT_FACTS, enter, maker, new_contract, post_contract

__all__ = ["maker"]


async def _resigned(client: AsyncClient, old: dict, filename: str) -> Response:
    return await post_contract(client, old["partnerId"], filename, replacesId=old["id"])


async def test_resigning_ends_the_old_contract_the_day_before_the_new_one_starts(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    old = await new_contract(maker, container)
    await enter(maker, old["instruments"][0]["id"], {**CONTRACT_FACTS, "renewal": "automatic"})
    new = (await _resigned(maker, old, "new.pdf")).json()
    assert new["partnerId"] == old["partnerId"]
    assert new["category"] == old["category"]
    assert new["replaces"]["id"] == old["id"]
    # Until the new contract has a start date, the old one runs on its own terms.
    before = (await maker.get(f"/contracts/{old['id']}")).json()
    assert before["replacedById"] == new["id"]
    assert before["replacedOn"] is None
    assert before["status"] == "auto_renewed"

    await enter(
        maker,
        new["instruments"][0]["id"],
        {"signed_on": "2024-01-01", "effective_from": "2024-01-01", "expires_on": "2026-12-31"},
    )
    after = (await maker.get(f"/contracts/{old['id']}")).json()
    assert after["status"] == "replaced"
    assert after["replacedOn"] == "2024-01-01"
    assert after["endOn"] == "2023-12-31"
    again = await _resigned(maker, old, "again.pdf")
    assert again.status_code == 409
    assert again.json()["code"] == "contract_already_resigned"


async def test_contracts_filter_by_renewal_clause_and_overlaps_are_flagged(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    first = await new_contract(maker, container)
    await enter(
        maker,
        first["instruments"][0]["id"],
        {**CONTRACT_FACTS, "expires_on": "2099-12-31", "renewal": "automatic"},
    )
    listed = await maker.get("/contracts", params={"renewal": "automatic"})
    assert [c["id"] for c in listed.json()["items"]] == [first["id"]]
    assert (await maker.get("/contracts", params={"renewal": "none"})).json()["total"] == 0

    # A second contract with the same partner, entered without "re-sign".
    second = await post_contract(maker, first["partnerId"], "second.pdf")
    await enter(
        maker,
        second.json()["instruments"][0]["id"],
        {"signed_on": "2024-01-01", "effective_from": "2024-01-01", "expires_on": "2099-12-31"},
    )
    detail = (await maker.get(f"/contracts/{first['id']}")).json()
    assert [c["id"] for c in detail["overlapping"]] == [second.json()["id"]]
