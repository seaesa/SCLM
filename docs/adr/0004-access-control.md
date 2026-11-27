# 0004. Permission-based access control

Status: Accepted · Date: 2026-11-17

## Context

Checks like `if user.role == "admin"` scattered across routes and screens become impossible to
audit and to change when a new role appears.

## Decision

- Code checks **permissions** (`Permission.USERS_READ`), never roles. Which role holds which
  permission is a [Casbin](https://casbin.org) RBAC policy, not code:
  `apps/api/src/app/shared/rbac/policy.csv` (`p, <role>, <permission>` rows; `g, <role>, <role>`
  for inheritance) with the model in `rbac/model.conf`. `shared/permissions.py` declares the
  `Role` and `Permission` enums and asks the enforcer (`has_permission`, `permissions_for`).
- Roles are deliberately few: `accountant` does the contract work, `director` approves and reads,
  `admin` manages users and inherits both (2026-11-25).
- Routes declare what they need with `Depends(require_permission(Permission.X))`; services that
  act on owned data also filter by owner (authorization is not only a route concern).
- The user's effective permissions are returned by `GET /users/me`; clients only use them to hide
  UI (`useHasPermission`), never as the security boundary.
- Roles are assigned by an admin on the Users screen (`users:manage`); the first admin by the
  operator command `uv run python -m app.cli create-user … --role admin`.

## Consequences

- Adding a role or moving a permission is a policy-file change; a test fails if the policy names
  an unknown permission or leaves one granted to nobody. Per-resource rules can later move to a
  richer Casbin model without touching call sites.
