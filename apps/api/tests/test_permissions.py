"""Access is granted by permission: a user without roles has none, admins can list users."""

from dishka import AsyncContainer
from httpx import AsyncClient

from app.modules.users.service import UserService
from app.shared.permissions import Permission, Role, permissions_for


async def _grant(container: AsyncContainer, email: str, *roles: Role) -> None:
    async with container() as request:
        users = await request.get(UserService)
        user = await users.get_by_email(email)
        assert user is not None
        await users.set_roles(user, list(roles))


async def test_users_without_roles_have_no_permissions(auth_client: AsyncClient) -> None:
    me = (await auth_client.get("/users/me")).json()
    assert me["roles"] == []
    assert me["permissions"] == []

    response = await auth_client.get("/users")
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


async def test_admins_can_list_users(auth_client: AsyncClient, container: AsyncContainer) -> None:
    await _grant(container, "jane@example.com", Role.ADMIN)

    me = (await auth_client.get("/users/me")).json()
    assert "users:read" in me["permissions"]

    response = await auth_client.get("/users")
    assert response.status_code == 200
    assert [user["email"] for user in response.json()["items"]] == ["jane@example.com"]


async def test_admins_inherit_what_accountants_and_directors_may_do(
    auth_client: AsyncClient, container: AsyncContainer
) -> None:
    await _grant(container, "jane@example.com", Role.ADMIN)
    permissions = set((await auth_client.get("/users/me")).json()["permissions"])
    assert {"users:manage", "contracts:register", "contracts:approve"} <= permissions


async def test_accountants_do_the_contract_work_and_directors_approve(
    auth_client: AsyncClient, container: AsyncContainer
) -> None:
    await _grant(container, "jane@example.com", Role.ACCOUNTANT)
    accountant = set((await auth_client.get("/users/me")).json()["permissions"])
    assert {"contracts:register", "fuel-prices:manage"} <= accountant
    assert "contracts:approve" not in accountant
    assert (await auth_client.get("/users")).status_code == 403

    await _grant(container, "jane@example.com", Role.DIRECTOR)
    director = set((await auth_client.get("/users/me")).json()["permissions"])
    assert "contracts:approve" in director
    assert "contracts:register" not in director


def test_the_policy_grants_only_known_permissions_and_each_one_to_someone() -> None:
    granted = permissions_for(list(Role))
    assert granted == set(Permission)
