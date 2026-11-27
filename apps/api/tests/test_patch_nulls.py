"""An explicit `null` for a non-nullable field must be a 422, never a database error."""

from httpx import AsyncClient


async def test_patch_me_full_name_null_is_validation_error(auth_client: AsyncClient) -> None:
    response = await auth_client.patch("/users/me", json={"fullName": None})

    assert response.status_code == 422
    details = response.json()["details"]
    assert details[0]["field"] == "fullName"
    assert details[0]["code"] == "null_not_allowed"
