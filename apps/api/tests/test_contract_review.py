"""Documents Spider drafts itself: draft → submitted → approved/rejected → signed → in force."""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from dishka import AsyncContainer
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.mail import OutboxEmailSender
from app.shared.permissions import Role
from tests.contract_factory import (
    CONTRACT_FACTS,
    enter,
    grant,
    maker,
    new_contract,
)
from tests.helpers import register_verified

__all__ = ["maker"]


@pytest.fixture
async def director(
    api_app: FastAPI, container: AsyncContainer, outbox: OutboxEmailSender
) -> AsyncIterator[AsyncClient]:
    """Dan approves; he has no right to register contracts."""
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as client:
        tokens = await register_verified(client, outbox, "dan@example.com", full_name="Dan")
        client.headers["Authorization"] = f"Bearer {tokens['accessToken']}"
        await grant(container, "dan@example.com", Role.DIRECTOR)
        yield client


async def drafted(maker: AsyncClient, container: AsyncContainer) -> dict[str, Any]:
    """A contract drafted from Spider's template: its contract document needs approval."""
    detail = await new_contract(maker, container, needsApproval="true")
    file_id = detail["fileId"]
    document = detail["instruments"][0]
    await enter(maker, document["id"], CONTRACT_FACTS)
    return {**detail, "fileId": file_id, "documentId": document["id"]}


async def signed_copy(client: AsyncClient, set_id: str) -> str:
    upload = await client.post(
        f"/document-sets/{set_id}/files",
        files={"file": ("signed.pdf", b"%PDF signed by both", "application/pdf")},
    )
    assert upload.status_code == 201, upload.text
    return str(upload.json()["id"])


async def test_a_drafted_contract_is_in_force_only_once_approved_and_signed(
    maker: AsyncClient, director: AsyncClient, container: AsyncContainer
) -> None:
    contract = await drafted(maker, container)
    document = f"/contract-instruments/{contract['documentId']}"
    assert contract["instruments"][0]["reviewState"] == "draft"
    assert contract["instruments"][0]["signingState"] == "unsigned"
    url = f"/contracts/{contract['id']}"
    assert (await maker.get(url)).json()["status"] == "draft"

    submitted = await maker.post(f"{document}/submit", json={"comment": "Prices from 2026"})
    assert submitted.status_code == 200, submitted.text
    approved = await director.post(f"{document}/approve", json={})
    assert approved.status_code == 200, approved.text
    assert approved.json()["instruments"][0]["approvedByName"] == "Dan"

    assert (await maker.get(url)).json()["status"] == "draft"
    waiting = await maker.get("/contracts", params={"isAwaitingSignature": True})
    assert [c["id"] for c in waiting.json()["items"]] == [contract["id"]]
    no_copy = await maker.put(f"{document}/signing", json={"state": "signed"})
    assert no_copy.status_code == 400
    assert no_copy.json()["code"] == "signed_copy_required"
    file_id = await signed_copy(maker, contract["dossierId"])
    signed = await maker.put(f"{document}/signing", json={"state": "signed", "fileId": file_id})
    assert signed.status_code == 200, signed.text
    assert signed.json()["instruments"][0]["fileId"] == file_id

    detail = (await maker.get(url)).json()
    assert detail["status"] == "expired"
    events = [(e["kind"], e["actorName"]) for e in detail["events"]]
    assert events == [
        ("created", "Jane"),
        ("edited", "Jane"),
        ("submitted", "Jane"),
        ("approved", "Dan"),
        ("signing", "Jane"),
    ]


async def test_a_drafted_addendum_counts_only_once_approved_and_signed(
    maker: AsyncClient, director: AsyncClient, container: AsyncContainer
) -> None:
    contract = await new_contract(maker, container)
    await enter(maker, contract["instruments"][0]["id"], CONTRACT_FACTS)
    added = await maker.post(
        f"/contracts/{contract['id']}/instruments",
        json={"kind": "addendum", "fileId": contract["fileId"], "needsApproval": True},
    )
    addendum = added.json()["instruments"][-1]
    await enter(
        maker,
        addendum["id"],
        {
            "number": "01",
            "summary": "Extended one year",
            "signed_on": "2023-03-01",
            "effective_from": "2023-03-01",
            "extends_to": "2024-03-14",
            "adjustments": "term",
        },
    )
    detail = (await maker.get(f"/contracts/{contract['id']}")).json()
    assert (detail["endOn"], detail["instruments"][-1]["isSettled"]) == ("2023-03-14", False)

    document = f"/contract-instruments/{addendum['id']}"
    await maker.post(f"{document}/submit", json={})
    await director.post(f"{document}/approve", json={})
    file_id = await signed_copy(maker, contract["dossierId"])
    await maker.put(f"{document}/signing", json={"state": "signed", "fileId": file_id})

    detail = (await maker.get(f"/contracts/{contract['id']}")).json()
    assert (detail["endOn"], detail["instruments"][-1]["isSettled"]) == ("2024-03-14", True)


async def test_rejecting_needs_a_comment_and_sends_the_draft_back(
    maker: AsyncClient, director: AsyncClient, container: AsyncContainer
) -> None:
    contract = await drafted(maker, container)
    document = f"/contract-instruments/{contract['documentId']}"
    await maker.post(f"{document}/submit", json={})

    silent = await director.post(f"{document}/reject", json={"comment": "  "})
    assert silent.status_code == 400
    assert silent.json()["code"] == "review_comment_required"

    rejected = await director.post(f"{document}/reject", json={"comment": "Wrong rate for Hue"})
    assert rejected.json()["instruments"][0]["reviewState"] == "rejected"

    # Approving a rejected draft is not possible until it is submitted again.
    stale = await director.post(f"{document}/approve", json={})
    assert stale.status_code == 409
    assert stale.json()["code"] == "review_state_invalid"
    resubmitted = await maker.post(f"{document}/submit", json={})
    assert resubmitted.json()["instruments"][0]["reviewState"] == "submitted"


async def test_only_approvers_decide_and_only_registrars_submit(
    maker: AsyncClient, director: AsyncClient, container: AsyncContainer
) -> None:
    contract = await drafted(maker, container)
    document = f"/contract-instruments/{contract['documentId']}"
    assert (await director.post(f"{document}/submit", json={})).status_code == 403
    await maker.post(f"{document}/submit", json={})
    assert (await maker.post(f"{document}/approve", json={})).status_code == 403


async def test_archive_documents_need_no_approval(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await new_contract(maker, container)
    document = contract["instruments"][0]
    assert (document["reviewState"], document["signingState"]) == (None, "signed")

    submit = await maker.post(f"/contract-instruments/{document['id']}/submit", json={})

    assert submit.status_code == 409
    assert submit.json()["code"] == "review_state_invalid"
