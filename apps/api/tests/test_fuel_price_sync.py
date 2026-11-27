"""Official fuel prices from Petrolimex: parsing the published list and recording it once."""

from datetime import date
from decimal import Decimal

from dishka import AsyncContainer
from httpx import AsyncClient

from app.modules.pricing.petrolimex import PublishedPrice, parse
from app.modules.pricing.service import PricingService
from tests.contract_factory import maker

__all__ = ["maker"]

# Product names are Vietnamese: cspell:ignore Vùng Xăng


def test_each_zone_becomes_a_fuel_type_dated_in_vietnam_time() -> None:
    prices = parse(
        [
            # 07:56 UTC is 14:56 in Vietnam, the day the price changed.
            {
                "Title": "DO 0,05S-II",
                "Zone1Price": 26340,
                "Zone2Price": 26860,
                "LastModified": "2026-11-19T07:56:27.785Z",
            },
            # 18:00 UTC is already the next day in Vietnam.
            {
                "Title": "Xăng E5 RON 92-II",
                "Zone1Price": 18570,
                "Zone2Price": None,
                "LastModified": "2026-11-19T18:00:00Z",
            },
        ]
    )
    assert prices == [
        PublishedPrice("DO 0,05S-II Vùng 1", date(2026, 11, 19), Decimal("26340")),
        PublishedPrice("DO 0,05S-II Vùng 2", date(2026, 11, 19), Decimal("26860")),
        PublishedPrice("Xăng E5 RON 92-II Vùng 1", date(2026, 11, 20), Decimal("18570")),
    ]


class _Source:
    name = "Petrolimex"

    def __init__(self, prices: list[PublishedPrice]) -> None:
        self.prices = prices

    async def fetch(self) -> list[PublishedPrice]:
        return self.prices


async def _sync(container: AsyncContainer, prices: list[PublishedPrice]) -> tuple[int, int, int]:
    async with container() as request:
        report = await (await request.get(PricingService)).sync_fuel_prices(_Source(prices))
    return report.added, report.updated, report.unchanged


async def test_sync_records_once_and_the_official_price_replaces_a_typed_one(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    on = date(2026, 11, 19)
    typed = await maker.post(
        "/fuel-prices",
        json={"fuelType": "DO 0,05S-II Vùng 1", "effectiveOn": on.isoformat(), "price": "26000"},
    )
    assert typed.status_code == 201
    official = [
        PublishedPrice("DO 0,05S-II Vùng 1", on, Decimal("26340")),
        PublishedPrice("DO 0,05S-II Vùng 2", on, Decimal("26860")),
    ]

    assert await _sync(container, official) == (1, 1, 0)
    assert await _sync(container, official) == (0, 0, 2)

    listed = (await maker.get("/fuel-prices", params={"fuelType": "DO 0,05S-II Vùng 1"})).json()
    [price] = listed["items"]
    assert (price["price"], price["source"], price["isOfficial"]) == (
        "26340.00",
        "Petrolimex",
        True,
    )
    locked = await maker.delete(f"/fuel-prices/{price['id']}")
    assert locked.status_code == 409
    assert locked.json()["code"] == "official_price_locked"


async def test_only_fuel_price_managers_can_start_a_sync(client: AsyncClient) -> None:
    response = await client.post("/fuel-prices/sync")
    assert response.status_code == 401
