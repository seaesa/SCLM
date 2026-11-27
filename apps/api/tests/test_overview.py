"""The dashboard counts what the owning modules hold, computed for today."""

from datetime import timedelta

from dishka import AsyncContainer
from httpx import AsyncClient

from app.shared.clock import business_today
from tests.contract_factory import CONTRACT_FACTS, enter, maker, new_contract

__all__ = ["maker"]


async def test_overview_counts_statuses_reviews_and_contracts_due_soon(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    published = await new_contract(maker, container)
    await enter(maker, published["instruments"][0]["id"], CONTRACT_FACTS)
    due = await new_contract(maker, container)
    end_on = business_today() + timedelta(days=40)
    await enter(
        maker,
        due["instruments"][0]["id"],
        {
            **CONTRACT_FACTS,
            "expires_on": end_on.isoformat(),
            "renewal": "automatic",
            "renewal_notice_days": "30",
        },
    )
    await new_contract(maker, container)

    response = await maker.get("/overview")

    assert response.status_code == 200
    body = response.json()
    assert sorted(body["contracts"]["byStatus"], key=lambda c: c["status"]) == [
        {"status": "active", "count": 1},
        {"status": "expired", "count": 1},
        {"status": "undetermined", "count": 1},
    ]
    assert (body["contracts"]["awaitingApproval"], body["contracts"]["awaitingSignature"]) == (0, 0)
    assert (body["contracts"]["expiringSoon"], body["contracts"]["noticeSoon"]) == (1, 1)


async def test_overview_needs_contract_access(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/overview")

    assert response.status_code == 403
