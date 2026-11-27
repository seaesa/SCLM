"""Scans are stored once by their bytes; files are found again by name or hash."""

import hashlib
import uuid
from pathlib import Path

from dishka import AsyncContainer
from httpx import AsyncClient

from app.modules.documents.files import walk
from app.modules.documents.models import DocumentSide
from app.modules.documents.schemas import StoreReport
from app.modules.documents.service import DocumentService
from app.shared.permissions import Role
from tests.contract_factory import grant, maker, new_contract

__all__ = ["maker"]


def _folder(root: Path) -> Path:
    """Two filings of the same contract scan, an addendum and an Office lock file."""
    folder = root / f"customers-{uuid.uuid4().hex[:6]}"
    (folder / "alpha").mkdir(parents=True)
    contract = f"contract {uuid.uuid4()}".encode()
    (folder / "alpha" / "contract.pdf").write_bytes(contract)
    (folder / "alpha" / "PL01.pdf").write_bytes(f"addendum {uuid.uuid4()}".encode())
    (folder / "alpha" / "~$lock.docx").write_bytes(b"office lock file")
    (folder / "beta.pdf").write_bytes(contract)
    return folder


async def _store(container: AsyncContainer, folder: Path) -> StoreReport:
    report = StoreReport()
    async with container() as request:
        service = await request.get(DocumentService)
        for item in walk(folder):
            await service.store(item, report)
    return report


async def test_storing_keeps_each_file_once_and_is_idempotent(
    container: AsyncContainer, tmp_path: Path
) -> None:
    folder = _folder(tmp_path)

    first = await _store(container, folder)
    assert (first.files_stored, first.files_already_stored) == (2, 1)

    again = await _store(container, folder)
    assert (again.files_stored, again.files_already_stored) == (0, 3)


async def test_filed_copies_are_found_by_name_or_hash_prefix(
    container: AsyncContainer, tmp_path: Path
) -> None:
    folder = _folder(tmp_path)
    await _store(container, folder)
    item = next(f for f in walk(folder) if f.path.endswith("PL01.pdf"))
    sha = hashlib.sha256(item.absolute.read_bytes()).hexdigest()
    async with container() as request:
        service = await request.get(DocumentService)
        file_id = (await service.file_ids([sha]))[sha]
        await service.archive_dossier(
            f"archive/{uuid.uuid4().hex}", DocumentSide.CUSTOMER, None, [(item.path, file_id)]
        )
        by_name = await service.locate(item.path)
        by_hash = await service.locate(sha[:12])

    assert [f.sha256 for f in by_name] == [sha]
    assert [f.path for f in by_hash] == [item.path]


async def test_files_are_downloaded_through_a_permission_checked_url(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    contract = await new_contract(maker, container)
    url = f"/document-sets/{contract['dossierId']}/files/{contract['fileId']}/download-url"

    await grant(container, "jane@example.com")  # roles taken away: the link is refused
    assert (await maker.get(url)).status_code == 403

    await grant(container, "jane@example.com", Role.ACCOUNTANT)
    response = await maker.get(url)
    assert response.status_code == 200
    assert "X-Amz-Signature" in response.json()["url"]


async def test_only_office_documents_and_pdfs_are_accepted(
    maker: AsyncClient, container: AsyncContainer
) -> None:
    set_id = (await new_contract(maker, container))["dossierId"]

    word = await maker.post(
        f"/document-sets/{set_id}/files",
        files={"file": ("phu-luc.docx", b"PK word", "application/octet-stream")},
    )
    script = await maker.post(
        f"/document-sets/{set_id}/files",
        files={"file": ("run.exe", b"MZ", "application/octet-stream")},
    )

    assert word.status_code == 201, word.text
    assert word.json()["contentType"].endswith("wordprocessingml.document")
    assert script.status_code == 400
    assert script.json()["code"] == "file_type_not_allowed"
