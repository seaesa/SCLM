"""The archive seed loads once: files by hash, re-signed contracts replace the earlier one, and a
second run changes nothing."""

import hashlib

from dishka import AsyncContainer
from httpx import AsyncClient

from app.modules.archive.schemas import ArchiveImportReport, ArchiveSeed
from app.modules.archive.service import ArchiveService
from app.modules.users.service import UserService
from tests.contract_factory import maker, new_contract
from tests.partner_factory import FakeSource, partner, sync

__all__ = ["maker"]

_SCANS = {
    "old": b"%PDF contract signed 2021",
    "addendum": b"%PDF addendum 01 of 2021",
    "new": b"%PDF contract re-signed 2023",
}


def _sha(name: str) -> str:
    return hashlib.sha256(_SCANS[name]).hexdigest()


def _seed() -> ArchiveSeed:
    return ArchiveSeed.model_validate(
        {
            "version": 1,
            "newPartners": [
                {
                    "code": "ARC-0312345678",
                    "name": "Printed only",
                    "taxCode": "0312345678",
                    "side": "customer",
                }
            ],
            "dossiers": [
                {
                    "key": "KH1/customer",
                    "partner": "KH1",
                    "side": "customer",
                    "files": [{"sha256": _sha(n), "path": f"KH1/{n}.pdf"} for n in _SCANS],
                    "contracts": [
                        {
                            "category": "customer",
                            "document": {
                                "kind": "contract",
                                "sha256": _sha("old"),
                                "facts": {
                                    "number": "01/2021",
                                    "signed_on": "2021-08-20",
                                    "renewal_notice_days": "about a month",
                                },
                            },
                            "annexes": [
                                {
                                    "kind": "addendum",
                                    "sha256": _sha("addendum"),
                                    "facts": {"number": "PL01", "effective_from": "2022-01-01"},
                                }
                            ],
                        },
                        {
                            "category": "customer",
                            "document": {
                                "kind": "contract",
                                "sha256": _sha("new"),
                                "facts": {"signed_on": "2023-08-21"},
                            },
                            "replaces": _sha("old"),
                        },
                    ],
                },
            ],
        }
    )


async def _import(container: AsyncContainer, seed: ArchiveSeed) -> ArchiveImportReport:
    async with container() as request:
        user = await (await request.get(UserService)).get_by_email("jane@example.com")
        assert user is not None
        return await (await request.get(ArchiveService)).import_seed(seed, user.id)


async def test_the_seed_links_renewals_and_a_second_run_adds_nothing(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    set_id = (await new_contract(maker, container))["dossierId"]
    for name, data in _SCANS.items():
        upload = await maker.post(
            f"/document-sets/{set_id}/files",
            files={"file": (f"{name}.pdf", data, "application/pdf")},
        )
        assert upload.status_code == 201, upload.text

    first = await _import(container, _seed())
    again = await _import(container, _seed())

    assert (first.partners_created, first.contracts_created, first.documents_added) == (1, 2, 3)
    assert first.replacements == 1
    # A fact the fields refuse is reported, never stored as a guess.
    assert first.rejected_facts == [f"{_sha('old')[:12]} renewal_notice_days=about a month"]
    assert (again.partners_created, again.contracts_created, again.documents_added) == (0, 0, 0)
    assert again.contracts_existing == 2

    listed = (await maker.get("/contracts", params={"sort": "newest"})).json()["items"]
    by_number = {c["signedOn"]: c for c in listed}
    old, new = by_number["2021-08-20"], by_number["2023-08-21"]
    assert (old["code"], new["code"]) == ("HĐKH-2021-0001", "HĐKH-2023-0001")
    assert (old["status"], old["endOn"]) == ("replaced", "2023-08-20")
    # No end date: in force until it is terminated or replaced.
    assert (new["status"], new["effectiveFrom"]) == ("active", "2023-08-21")
    assert old["addendumCount"] == 1

    # What the archive says stays on record: neither the contract nor its document can go.
    detail = (await maker.get(f"/contracts/{old['id']}")).json()
    assert detail["isImported"] is True
    assert detail["canDelete"] is False
    assert detail["instruments"][0]["canDelete"] is False
    assert detail["replacedBy"]["code"] == "HĐKH-2023-0001"
    assert detail["noticeOn"] is None
    assert [e["kind"] for e in detail["events"]] == ["imported"]
    refused = await maker.delete(f"/contracts/{old['id']}")
    assert refused.json()["code"] == "contract_from_archive"
    refused = await maker.delete(f"/contract-instruments/{detail['instruments'][0]['id']}")
    assert refused.json()["code"] == "contract_document_required"


async def test_nothing_is_imported_while_a_scan_is_not_stored(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    await sync(container, FakeSource(partner("KH1", "Masan")))

    report = await _import(container, _seed())

    assert sorted(report.missing_files) == sorted(_sha(n) for n in _SCANS)
    assert report.contracts_created == 0
