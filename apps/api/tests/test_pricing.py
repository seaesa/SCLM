"""Price tables govern orders only while their contract is in force, and are seen only by those
allowed to see that side's prices."""
# Price lines are Vietnamese: cspell:ignore chuyển chuyến Bình SASCO tấn

from typing import Any

from dishka import AsyncContainer
from httpx import AsyncClient

from app.shared.permissions import Role
from tests.contract_factory import CONTRACT_FACTS, enter, grant, maker, new_contract

__all__ = ["maker"]

_LINE = {
    "service": "Vận chuyển",
    "origin": "Kho Tân Bình",
    "destination": "SASCO",
    "vehicle": "Xe 1 tấn",
    "unit": "chuyến",
    "unitPrice": "1525700",
    "page": 3,
}


async def _priced(maker: AsyncClient, container: AsyncContainer) -> dict[str, Any]:
    contract = await new_contract(maker, container)
    instrument_id = contract["instruments"][0]["id"]
    await enter(
        maker,
        instrument_id,
        # No start and no signing date: the contract cannot be in force yet.
        {k: v for k, v in CONTRACT_FACTS.items() if k not in {"effective_from", "signed_on"}},
    )
    table = await maker.post(
        "/price-tables",
        json={
            "instrumentId": instrument_id,
            "effectiveFrom": "2022-03-15",
            "mode": "replace",
            "page": 3,
        },
    )
    assert table.status_code == 201, table.text
    lines = await maker.post(f"/price-tables/{table.json()['id']}/lines", json={"lines": [_LINE]})
    assert lines.status_code == 201, lines.text
    return {**contract, "instrumentId": instrument_id, "lineId": lines.json()[0]["id"]}


async def _lines(client: AsyncClient, contract: dict[str, Any]) -> list[dict[str, Any]]:
    response = await client.get(f"/contracts/{contract['id']}/pricing")
    assert response.status_code == 200, response.text
    return [line for table in response.json()["tables"] for line in table["lines"]]


async def test_directors_read_prices_but_do_not_enter_them(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await _priced(maker, container)
    await grant(container, "jane@example.com", Role.DIRECTOR)
    assert (await maker.get(f"/contracts/{contract['id']}/pricing")).status_code == 200
    withdraw = await maker.post(f"/price-lines/{contract['lineId']}/withdraw", json={})
    assert withdraw.status_code == 403


async def test_correcting_a_price_keeps_the_old_one_on_file(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await _priced(maker, container)
    await enter(maker, contract["instrumentId"], {"effective_from": "2022-03-15"})
    corrected = {**_LINE, "unitPrice": "1525800"}
    response = await maker.put(
        f"/price-lines/{contract['lineId']}", json={**corrected, "reason": "Misread a digit"}
    )
    assert response.status_code == 200, response.text
    [priced] = await _lines(maker, contract)
    assert priced["unitPrice"] == "1525800.00"
    again = await maker.post(
        f"/price-lines/{contract['lineId']}/withdraw", json={"reason": "Twice"}
    )
    assert again.json()["code"] == "already_withdrawn"


async def test_fuel_adjustment_proposes_prices_from_the_clause(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await _priced(maker, container)
    clause = await maker.post(
        "/fuel-clauses",
        json={
            "instrumentId": contract["instrumentId"],
            "fuelType": "DO 0,05S",
            "basePrice": "23320",
            "baseOn": "2022-03-01",
            "share": "0.35",
            "threshold": "0.10",
            "lagDays": 10,
            "rounding": "down_100",
            "isCumulative": True,
            "page": 4,
        },
    )
    assert clause.status_code == 201, clause.text
    for on, price in [("2022-04-01", "24000"), ("2022-05-01", "25760")]:
        created = await maker.post(
            "/fuel-prices", json={"fuelType": "DO 0,05S", "effectiveOn": on, "price": price}
        )
        assert created.status_code == 201, created.text
    duplicate = await maker.post(
        "/fuel-prices", json={"fuelType": "DO 0,05S", "effectiveOn": "2022-05-01", "price": "1"}
    )
    assert duplicate.json()["code"] == "fuel_price_exists"

    response = await maker.get(
        f"/contracts/{contract['id']}/fuel-adjustment", params={"on": "2022-06-01"}
    )
    body = response.json()
    assert body["proposal"]["effectiveOn"] == "2022-05-11"
    assert [line["proposedPrice"] for line in body["lines"]] == ["1581500"]


async def test_a_later_table_shows_each_price_against_the_one_it_replaces(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await _priced(maker, container)
    table = await maker.post(
        "/price-tables",
        json={
            "instrumentId": contract["instrumentId"],
            "effectiveFrom": "2023-01-01",
            "mode": "amend",
            "page": 4,
        },
    )
    await maker.post(
        f"/price-tables/{table.json()['id']}/lines",
        json={"lines": [{**_LINE, "unitPrice": "1581500"}]},
    )

    pricing = (await maker.get(f"/contracts/{contract['id']}/pricing")).json()

    first, later = (t["lines"][0] for t in pricing["tables"])
    assert (first["previousPrice"], first["change"]) == (None, None)
    assert (later["previousPrice"], later["change"]) == ("1525700.00", "0.0366")
