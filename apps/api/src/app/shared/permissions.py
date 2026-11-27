"""Who may do what. Endpoints check permissions, never roles. Which role holds which permission
is a Casbin RBAC policy (`rbac/policy.csv`, model `rbac/model.conf`): accountants do the contract
work, directors approve, admins manage users and inherit both. Both enums are exported through
OpenAPI, so the frontend gates UI with the same vocabulary."""

from enum import StrEnum
from functools import cache
from pathlib import Path

import casbin

_RBAC = Path(__file__).with_name("rbac")


class Role(StrEnum):
    ADMIN = "admin"
    ACCOUNTANT = "accountant"
    DIRECTOR = "director"


class Permission(StrEnum):
    USERS_READ = "users:read"
    USERS_MANAGE = "users:manage"
    PARTNERS_READ = "partners:read"
    PARTNERS_SYNC = "partners:sync"
    PARTNERS_ASSIGN = "partners:assign"
    CONTRACTS_READ = "contracts:read"
    CONTRACTS_REGISTER = "contracts:register"
    CONTRACTS_APPROVE = "contracts:approve"
    CONTRACT_FILES_DOWNLOAD = "contract-files:download"
    SELL_PRICES_READ = "sell-prices:read"
    BUY_PRICES_READ = "buy-prices:read"
    FUEL_PRICES_MANAGE = "fuel-prices:manage"
    AUDIT_READ = "audit:read"


@cache
def _enforcer() -> casbin.Enforcer:
    return casbin.Enforcer(str(_RBAC / "model.conf"), str(_RBAC / "policy.csv"))


def has_permission(roles: list[Role], permission: Permission) -> bool:
    enforcer = _enforcer()
    return any(enforcer.enforce(Role(role).value, permission.value) for role in roles)


def permissions_for(roles: list[Role]) -> frozenset[Permission]:
    """Every permission the roles grant, inherited ones included."""
    enforcer = _enforcer()
    return frozenset(
        Permission(rule[1])
        for role in roles
        for rule in enforcer.get_implicit_permissions_for_user(Role(role).value)
    )
