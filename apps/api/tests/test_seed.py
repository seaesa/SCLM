"""A seed bundle loads users and partners once; a second run skips unchanged steps."""

import json
from pathlib import Path

from dishka import AsyncContainer

from app.modules.seed.manifest import SeedManifest, SeedStep
from app.modules.seed.service import SeedService
from app.modules.users.service import UserService
from tests.conftest import OutboxEmailSender


def _bundle(tmp_path: Path) -> SeedManifest:
    (tmp_path / "users.json").write_text(
        json.dumps([{"email": "ann@example.com", "fullName": "Ann", "roles": ["accountant"]}])
    )
    (tmp_path / "customers.json").write_text(
        json.dumps([{"code": "KH0001", "company_name": "ACME", "tax_code": "0101010101"}])
    )
    return SeedManifest.model_validate(
        {"users": "users.json", "partners": {"customers": ["customers.json"]}}
    )


async def _run(container: AsyncContainer, bundle: Path, manifest: SeedManifest) -> dict[str, str]:
    async with container() as request:
        service = await request.get(SeedService)
        results = await service.run(bundle, manifest, [SeedStep.USERS, SeedStep.PARTNERS], False)
    return {r.step: r.outcome for r in results}


async def test_users_are_invited_and_unchanged_steps_are_skipped(
    container: AsyncContainer, outbox: OutboxEmailSender, tmp_path: Path
) -> None:
    manifest = _bundle(tmp_path)

    first = await _run(container, tmp_path, manifest)
    again = await _run(container, tmp_path, manifest)

    assert first == {"users": "applied", "partners": "applied"}
    assert again == {"users": "skipped", "partners": "skipped"}
    async with container() as request:
        user = await (await request.get(UserService)).get_by_email("ann@example.com")
    assert user is not None
    assert user.roles == ["accountant"]
    # The invitee chooses a password through the emailed link; none is stored in the bundle.
    assert [m.to for m in outbox.messages] == ["ann@example.com"]
