"""Accounts are created by an administrator; the new user sets a password from an email."""

import pytest
from dishka import AsyncContainer
from httpx import AsyncClient

from app.core.mail import OutboxEmailSender
from app.shared.permissions import Role
from tests.contract_factory import grant


@pytest.fixture
async def admin(auth_client: AsyncClient, container: AsyncContainer) -> AsyncClient:
    await grant(container, "jane@example.com", Role.ADMIN)
    return auth_client


async def test_an_invited_user_gets_a_set_password_email(
    admin: AsyncClient, outbox: OutboxEmailSender
) -> None:
    response = await admin.post(
        "/users",
        json={"email": "bob@example.com", "fullName": "Bob", "roles": ["director", "accountant"]},
    )

    assert response.status_code == 201, response.text
    assert response.json()["roles"] == ["accountant", "director"]
    assert any(m.to == "bob@example.com" and "token=" in m.text for m in outbox.messages)
    listed = (await admin.get("/users", params={"role": "director", "pageSize": 20})).json()
    assert (listed["total"], listed["items"][0]["email"]) == (1, "bob@example.com")


async def test_an_admin_deactivates_a_user(admin: AsyncClient) -> None:
    created = await admin.post(
        "/users", json={"email": "bob@example.com", "fullName": "Bob", "roles": ["accountant"]}
    )
    user_id = created.json()["id"]

    response = await admin.patch(f"/users/{user_id}", json={"isActive": False})

    assert response.status_code == 200, response.text
    assert response.json()["isActive"] is False


async def test_admins_cannot_lock_themselves_out(admin: AsyncClient) -> None:
    me = (await admin.get("/users/me")).json()

    demoted = await admin.patch(f"/users/{me['id']}", json={"roles": ["accountant"]})
    deactivated = await admin.patch(f"/users/{me['id']}", json={"isActive": False})

    assert demoted.status_code == deactivated.status_code == 403
    assert demoted.json()["code"] == "own_access_required"


async def test_only_admins_manage_users(
    auth_client: AsyncClient, container: AsyncContainer
) -> None:
    await grant(container, "jane@example.com", Role.DIRECTOR)

    response = await auth_client.post(
        "/users", json={"email": "bob@example.com", "fullName": "Bob", "roles": ["accountant"]}
    )

    assert response.status_code == 403
