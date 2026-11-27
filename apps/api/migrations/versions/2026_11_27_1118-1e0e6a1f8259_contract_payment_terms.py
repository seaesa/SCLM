"""contract payment terms

Revision ID: 1e0e6a1f8259
Revises: a0acde13b296
Create Date: 2026-11-27 11:18:15.808325

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1e0e6a1f8259"
down_revision: str | Sequence[str] | None = "a0acde13b296"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_COLUMNS = (
    ("payment_days", sa.Integer()),
    ("payment_from", sa.String(length=16)),
    ("statement_cutoff", sa.String(length=16)),
)


def upgrade() -> None:
    # Filled by the next refresh of the contracts.
    for name, type_ in _COLUMNS:
        op.add_column("contracts", sa.Column(name, type_, nullable=True), if_not_exists=True)


def downgrade() -> None:
    for name, _ in reversed(_COLUMNS):
        op.drop_column("contracts", name, if_exists=True)
