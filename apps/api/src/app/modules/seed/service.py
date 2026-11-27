import asyncio
import hashlib
from collections.abc import Callable, Coroutine, Iterable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.archive.schemas import ArchiveSeed
from app.modules.archive.service import ArchiveService
from app.modules.auth.service import AuthService
from app.modules.documents.files import walk
from app.modules.documents.schemas import StoreReport
from app.modules.documents.service import DocumentService
from app.modules.partners.service import PartnerService
from app.modules.partners.source import JsonFilePartnerSource
from app.modules.pricing.petrolimex import FuelPriceSource
from app.modules.pricing.service import PricingService
from app.modules.seed.manifest import SeedManifest, SeedStep, SeedUser
from app.modules.seed.repository import SeedRunRepository
from app.modules.users.schemas import UserInvite
from app.modules.users.service import UserService
from app.shared.clock import business_today
from app.shared.schemas import Schema

_USERS = TypeAdapter(list[SeedUser])


class StepResult(Schema):
    step: SeedStep
    # "applied", "skipped" (input unchanged since the last run) or "not_configured".
    outcome: str
    report: dict[str, Any] = Field(default_factory=dict)


class SeedError(Exception):
    """The bundle cannot be seeded as it is; nothing of the failing step was kept."""


def _hash_files(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _hash_tree(folders: Iterable[Path]) -> str:
    # Names, sizes and modification times: rereading gigabytes of scans to learn that nothing
    # changed would make every deploy slow.
    digest = hashlib.sha256()
    for folder in folders:
        for item in walk(folder):
            stat = item.absolute.stat()
            digest.update(f"{item.path}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode())
    return digest.hexdigest()


class SeedService:
    """Loads a seed bundle step by step. Every step is idempotent, and a step whose input has
    not changed since its last successful run is skipped, so this can run on every deploy."""

    def __init__(
        self,
        session: AsyncSession,
        runs: SeedRunRepository,
        users: UserService,
        auth: AuthService,
        partners: PartnerService,
        documents: DocumentService,
        archive: ArchiveService,
        pricing: PricingService,
        fuel_source: FuelPriceSource,
    ) -> None:
        self.session = session
        self.runs = runs
        self.users = users
        self.auth = auth
        self.partners = partners
        self.documents = documents
        self.archive = archive
        self.pricing = pricing
        self.fuel_source = fuel_source

    async def run(
        self, bundle: Path, manifest: SeedManifest, steps: Iterable[SeedStep], force: bool
    ) -> list[StepResult]:
        def at(relative: str) -> Path:
            path = (bundle / relative).resolve()
            if not path.exists():
                raise SeedError(f"Missing in the bundle: {relative}")
            return path

        plans: dict[
            SeedStep, tuple[Callable[[], str], Callable[[], Coroutine[Any, Any, BaseModel]]]
        ] = {}
        if manifest.users:
            users_file = at(manifest.users)
            plans[SeedStep.USERS] = (
                lambda: _hash_files([users_file]),
                lambda: self._users(users_file),
            )
        partner_files = [at(p) for p in manifest.partners.customers + manifest.partners.suppliers]
        if partner_files:
            source = JsonFilePartnerSource(
                [at(p) for p in manifest.partners.customers],
                [at(p) for p in manifest.partners.suppliers],
            )
            plans[SeedStep.PARTNERS] = (
                lambda: _hash_files(partner_files),
                lambda: self.partners.sync(source),
            )
        folders = [at(f) for f in manifest.files.customers + manifest.files.suppliers]
        if folders:
            plans[SeedStep.FILES] = (lambda: _hash_tree(folders), lambda: self._files(folders))
        if manifest.archive:
            archive_file = at(manifest.archive)
            author = manifest.archive_author
            plans[SeedStep.ARCHIVE] = (
                lambda: _hash_files([archive_file]),
                lambda: self._archive(archive_file, author),
            )
        # Official prices change every few days: fetch at most once a day.
        plans[SeedStep.FUEL_PRICES] = (
            lambda: business_today().isoformat(),
            lambda: self.pricing.sync_fuel_prices(self.fuel_source),
        )

        results: list[StepResult] = []
        for step in sorted(set(steps), key=list(SeedStep).index):
            if step not in plans:
                results.append(StepResult(step=step, outcome="not_configured"))
                continue
            checksum_of, apply = plans[step]
            checksum = await asyncio.to_thread(checksum_of)
            last = await self.runs.of_step(step)
            if last is not None and last.checksum == checksum and not force:
                results.append(StepResult(step=step, outcome="skipped", report=last.report))
                continue
            report = (await apply()).model_dump(mode="json", by_alias=True)
            if last is None:
                await self.runs.create(step=step, checksum=checksum, report=report)
            else:
                await self.runs.update(last, checksum=checksum, report=report)
            await self.session.commit()
            results.append(StepResult(step=step, outcome="applied", report=report))
        return results

    async def _users(self, path: Path) -> BaseModel:
        """Opens missing accounts and emails each a set-password link; existing accounts are left
        as they are, so roles changed in the app are not undone by the next deploy."""
        people = _USERS.validate_json(await asyncio.to_thread(path.read_bytes))
        invited: list[str] = []
        for person in people:
            if await self.users.get_by_email(person.email) is not None:
                continue
            user = await self.users.invite(
                UserInvite(email=person.email, full_name=person.full_name, roles=person.roles)
            )
            await self.auth.forgot_password(user.email, "vi")
            invited.append(user.email)
        return UsersReport(invited=invited, existing=len(people) - len(invited))

    async def _files(self, folders: list[Path]) -> BaseModel:
        report = StoreReport()
        for folder in folders:
            for item in walk(folder):
                await self.documents.store(item, report)
        return report

    async def _archive(self, path: Path, author: str | None) -> BaseModel:
        if author is None:
            raise SeedError("seed.json needs archiveAuthor to record archive contracts")
        actor = await self.users.get_by_email(author)
        if actor is None:
            raise SeedError(f"archiveAuthor {author} is not a user: seed the users first")
        seed = ArchiveSeed.model_validate_json(await asyncio.to_thread(path.read_bytes))
        report = await self.archive.import_seed(seed, actor.id)
        if report.missing_files:
            raise SeedError(f"{len(report.missing_files)} archive files are not stored: seed files")
        return report


class UsersReport(Schema):
    invited: list[str]
    existing: int
