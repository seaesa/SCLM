"""Removing what was recorded by mistake, and annulling an addendum by another."""

from dishka import AsyncContainer
from httpx import AsyncClient

from tests.contract_factory import CONTRACT_FACTS, add_document, enter, maker, new_contract

__all__ = ["maker"]

_PRICE = {"number": "PL01", "signed_on": "2022-06-01", "adjustments": "price"}


async def test_a_document_is_deleted_unless_it_is_in_review(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await new_contract(maker, container)
    signed = await add_document(maker, contract, "addendum", _PRICE)
    response = await maker.delete(f"/contract-instruments/{signed}")
    assert response.status_code == 200, response.text
    detail = response.json()
    assert [i["id"] for i in detail["instruments"]] == [contract["instruments"][0]["id"]]
    assert detail["events"][-1]["kind"] == "deleted"

    draft = (
        await maker.post(
            f"/contracts/{contract['id']}/instruments",
            json={"kind": "addendum", "fileId": contract["fileId"], "needsApproval": True},
        )
    ).json()["instruments"][-1]
    await enter(maker, draft["id"], {**_PRICE, "summary": "New prices"})
    submitted = await maker.post(f"/contract-instruments/{draft['id']}/submit", json={})
    assert submitted.status_code == 200, submitted.text
    refused = await maker.delete(f"/contract-instruments/{draft['id']}")
    assert refused.status_code == 409
    assert refused.json()["code"] == "document_locked"


async def test_a_contract_is_deleted_unless_a_document_is_in_review(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    in_review = await new_contract(maker, container, needsApproval="true")
    main = in_review["instruments"][0]["id"]
    await enter(maker, main, CONTRACT_FACTS)
    assert (await maker.post(f"/contract-instruments/{main}/submit", json={})).status_code == 200
    refused = await maker.delete(f"/contracts/{in_review['id']}")
    assert refused.status_code == 409
    assert refused.json()["code"] == "contract_locked"

    mistake = await new_contract(maker, container, filename="mistake.pdf")
    assert (await maker.delete(f"/contracts/{mistake['id']}")).status_code == 204
    assert (await maker.get(f"/contracts/{mistake['id']}")).status_code == 404
    assert (await maker.get(f"/document-sets/{mistake['dossierId']}")).status_code == 404


async def test_a_file_is_removed_only_while_no_document_uses_it(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await new_contract(maker, container)
    used = await maker.delete(f"/contracts/{contract['id']}/files/{contract['fileId']}")
    assert used.status_code == 409
    assert used.json()["code"] == "file_in_use"

    extra = await maker.post(
        f"/document-sets/{contract['dossierId']}/files",
        files={"file": ("wrong.pdf", b"%PDF wrong upload", "application/pdf")},
    )
    file_id = extra.json()["id"]
    removed = await maker.delete(f"/contracts/{contract['id']}/files/{file_id}")
    assert removed.status_code == 204
    files = (await maker.get(f"/document-sets/{contract['dossierId']}")).json()["files"]
    assert [f["id"] for f in files] == [contract["fileId"]]


async def test_an_annulled_addendum_no_longer_extends_the_contract(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await new_contract(maker, container)
    extension = await add_document(
        maker,
        contract,
        "addendum",
        {
            "number": "PL02",
            "signed_on": "2023-03-01",
            "adjustments": "term",
            "extends_to": "2024-03-14",
        },
    )
    url = f"/contracts/{contract['id']}"
    detail = (await maker.get(url)).json()
    assert detail["endOn"] == "2024-03-14"
    code = next(i["code"] for i in detail["instruments"] if i["id"] == extension)
    await add_document(
        maker,
        contract,
        "addendum",
        {"number": "PL03", "signed_on": "2023-04-01", "adjustments": "revoke", "revokes": code},
    )
    detail = (await maker.get(url)).json()
    assert detail["endOn"] is None
    annulled = next(i for i in detail["instruments"] if i["id"] == extension)
    assert annulled["standing"] == "revoked"
