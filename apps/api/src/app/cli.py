"""Operator commands, run from `apps/api`:

    uv run python -m app.cli create-user <email> "<full name>" --role admin
    uv run python -m app.cli set-roles <email> <role> [<role> ...]
    uv run python -m app.cli set-password <email>
    uv run python -m app.cli seed <bundle> [--only users partners files archive fuel-prices] [--force]
    uv run python -m app.cli find-file <part of a file name or hash>
    uv run python -m app.cli apply-facts <changes.json> <email of the person recording them>

`create-user` and `set-password` ask for the password on the terminal so it never lands in shell history.
The account is marked verified: an admin vouches for the address."""

import argparse
import asyncio
import getpass
import json
from pathlib import Path

from dishka import AsyncContainer

from app.core.worker_container import with_container
from app.modules.contracts.service import ContractService
from app.modules.documents.service import DocumentService
from app.modules.pricing.petrolimex import FuelPriceSource
from app.modules.pricing.service import PricingService
from app.modules.seed.manifest import SeedManifest, SeedStep
from app.modules.seed.service import SeedError, SeedService
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService
from app.shared.clock import business_today
from app.shared.permissions import Role

ROLE_CHOICES = [role.value for role in Role]
STEP_CHOICES = [step.value for step in SeedStep]


async def create_user(
    container: AsyncContainer, email: str, full_name: str, password: str, roles: list[Role]
) -> None:
    async with container() as request:
        users = await request.get(UserService)
        user = await users.create(UserCreate(email=email, full_name=full_name, password=password))
        await users.mark_verified(user)
        await users.set_roles(user, roles)
    print(f"Created {email} with roles: {', '.join(roles) or '(none)'}")


async def set_roles(container: AsyncContainer, email: str, roles: list[Role]) -> None:
    async with container() as request:
        users = await request.get(UserService)
        user = await users.get_by_email(email)
        if user is None:
            raise SystemExit(f"No user with email {email}")
        await users.set_roles(user, roles)
    print(f"{email} now has roles: {', '.join(roles) or '(none)'}")


async def set_password(container: AsyncContainer, email: str, password: str) -> None:
    async with container() as request:
        users = await request.get(UserService)
        user = await users.get_by_email(email)
        if user is None:
            raise SystemExit(f"No user with email {email}")
        await users.set_password(user, password)
    print(f"Password changed for {email}; their sessions are signed out")


async def sync_fuel_prices(container: AsyncContainer) -> None:
    async with container() as request:
        service = await request.get(PricingService)
        report = await service.sync_fuel_prices(await request.get(FuelPriceSource))
    print(report.model_dump_json(indent=2))


async def seed(container: AsyncContainer, bundle: Path, steps: list[SeedStep], force: bool) -> None:
    manifest = SeedManifest.model_validate_json(
        await asyncio.to_thread((bundle / "seed.json").read_bytes)
    )
    async with container() as request:
        service = await request.get(SeedService)
        try:
            results = await service.run(bundle, manifest, steps, force)
        except SeedError as error:
            raise SystemExit(str(error)) from error
    for result in results:
        print(f"{result.step}: {result.outcome}")
        if result.outcome == "applied":
            print(json.dumps(result.report, ensure_ascii=False, indent=2))


async def find_file(container: AsyncContainer, term: str) -> None:
    async with container() as request:
        found = await (await request.get(DocumentService)).locate(term)
    for item in found:
        print(f"{item.path}\n  {item.storage_key}  {item.size} bytes  ({item.dossier})")
    print(f"{len(found)} found")


async def apply_facts(container: AsyncContainer, path: Path, email: str) -> None:
    """`changes.json` maps a document code to the facts to record: {"HĐKH-2024-0001": {...}}."""
    changes = json.loads(await asyncio.to_thread(path.read_bytes))
    async with container() as request:
        user = await (await request.get(UserService)).get_by_email(email)
        if user is None:
            raise SystemExit(f"No user {email}")
        unknown = await (await request.get(ContractService)).apply_facts(changes, user.id)
    print(f"Documents: {len(changes) - len(unknown)} recorded, {len(unknown)} not found")
    for code in unknown:
        print(f"  not found: {code}")


async def refresh_contracts(container: AsyncContainer) -> None:
    async with container() as request:
        changed = await (await request.get(ContractService)).refresh_all(business_today())
    print(f"Contracts updated: {changed}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    commands = parser.add_subparsers(dest="command", required=True)

    create_cmd = commands.add_parser("create-user", help="Create a verified account")
    create_cmd.add_argument("email")
    create_cmd.add_argument("full_name")
    create_cmd.add_argument("--role", action="append", default=[], choices=ROLE_CHOICES)

    roles_cmd = commands.add_parser("set-roles", help="Replace the roles of an existing user")
    roles_cmd.add_argument("email")
    roles_cmd.add_argument("roles", nargs="*", choices=ROLE_CHOICES)

    password_cmd = commands.add_parser(
        "set-password", help="Set a password when the set-password email cannot be used"
    )
    password_cmd.add_argument("email")

    seed_cmd = commands.add_parser("seed", help="Load a seed bundle (see modules/seed/manifest)")
    seed_cmd.add_argument("bundle", type=Path)
    seed_cmd.add_argument("--only", nargs="*", choices=STEP_CHOICES, default=STEP_CHOICES)
    seed_cmd.add_argument("--force", action="store_true", help="Run steps whose input is unchanged")
    find_cmd = commands.add_parser("find-file", help="Locate stored files by name or hash")
    find_cmd.add_argument("term")
    apply_cmd = commands.add_parser(
        "apply-facts", help="Record facts read back from the documents, as edits in the history"
    )
    apply_cmd.add_argument("changes", type=Path)
    apply_cmd.add_argument("email")
    commands.add_parser(
        "refresh-contracts",
        help="Recompute stored statuses and issue missing codes (run once after an upgrade)",
    )

    commands.add_parser("sync-fuel-prices", help="Record the fuel prices Petrolimex publishes now")

    args = parser.parse_args()
    if args.command == "create-user":
        password = getpass.getpass("Password (min 8 characters): ")
        roles = [Role(r) for r in args.role]
        asyncio.run(
            with_container(lambda c: create_user(c, args.email, args.full_name, password, roles))
        )
    elif args.command == "set-roles":
        roles = [Role(r) for r in args.roles]
        asyncio.run(with_container(lambda c: set_roles(c, args.email, roles)))
    elif args.command == "set-password":
        password = getpass.getpass("Password (min 8 characters): ")
        asyncio.run(with_container(lambda c: set_password(c, args.email, password)))
    elif args.command == "seed":
        steps = [SeedStep(step) for step in args.only]
        asyncio.run(with_container(lambda c: seed(c, args.bundle, steps, args.force)))
    elif args.command == "find-file":
        asyncio.run(with_container(lambda c: find_file(c, args.term)))
    elif args.command == "sync-fuel-prices":
        asyncio.run(with_container(sync_fuel_prices))
    elif args.command == "apply-facts":
        asyncio.run(with_container(lambda c: apply_facts(c, args.changes, args.email)))
    elif args.command == "refresh-contracts":
        asyncio.run(with_container(refresh_contracts))


if __name__ == "__main__":
    main()
