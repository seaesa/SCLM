"""Official retail fuel prices published by Petrolimex.

The petrolimex.com.vn price widget reads one CMS collection through the public portal API; this
module asks for the same collection. The answer holds only the prices in force now, each with the
time it was last changed, so history accumulates from regular syncs.
"""

# Zone names are Vietnamese: cspell:ignore Vùng

import base64
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol
from zoneinfo import ZoneInfo

import httpx

SOURCE_NAME = "Petrolimex"
_URL = "https://portals.petrolimex.com.vn/~apis/portals/cms.item/search"
# Identifiers of the price collection, as sent by the petrolimex.com.vn price widget.
_QUERY = {
    "FilterBy": {
        "And": [
            {"SystemID": {"Equals": "6783dc1271ff449e95b74a9520964169"}},
            {"RepositoryID": {"Equals": "a95451e23b474fe5886bfb7cf843f53c"}},
            {"RepositoryEntityID": {"Equals": "3801378fe1e045b1afa10de7c5776124"}},
            {"Status": {"Equals": "Published"}},
        ]
    },
    "SortBy": {"LastModified": "Descending"},
    "Pagination": {"TotalRecords": -1, "TotalPages": 0, "PageSize": 0, "PageNumber": 0},
}
# Prices change at 15:00 Vietnam time; the date of the change is the date it takes effect.
_VIETNAM = ZoneInfo("Asia/Ho_Chi_Minh")
_ZONES = (("Zone1Price", "Vùng 1"), ("Zone2Price", "Vùng 2"))


@dataclass(frozen=True)
class PublishedPrice:
    fuel_type: str
    effective_on: date
    price: Decimal


class FuelPriceSource(Protocol):
    name: str

    async def fetch(self) -> list[PublishedPrice]: ...


def fuel_type_name(title: str, zone: str) -> str:
    """The fuel type a contract cites, e.g. "DO 0,05S-II Vùng 1"."""
    return f"{title.strip()} {zone}"


def parse(objects: list[dict[str, Any]]) -> list[PublishedPrice]:
    """One price per product and zone; an entry without a price is skipped, never guessed."""
    prices: list[PublishedPrice] = []
    for item in objects:
        changed = datetime.fromisoformat(item["LastModified"].replace("Z", "+00:00"))
        for key, zone in _ZONES:
            value = item.get(key)
            if value is None or Decimal(str(value)) <= 0:
                continue
            prices.append(
                PublishedPrice(
                    fuel_type=fuel_type_name(item["Title"], zone),
                    effective_on=changed.astimezone(_VIETNAM).date(),
                    price=Decimal(str(value)),
                )
            )
    return prices


class PetrolimexPrices:
    name = SOURCE_NAME

    async def fetch(self) -> list[PublishedPrice]:
        request = base64.urlsafe_b64encode(
            json.dumps(_QUERY, separators=(",", ":")).encode()
        ).decode()
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(_URL, params={"x-request": request})
            response.raise_for_status()
        return parse(response.json()["Objects"])
