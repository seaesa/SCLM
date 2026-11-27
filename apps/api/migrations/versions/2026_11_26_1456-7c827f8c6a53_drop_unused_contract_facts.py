"""drop unused contract facts

Revision ID: 7c827f8c6a53
Revises: 7f8be4fd9e68
Create Date: 2026-11-26 14:56:25.621452

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c827f8c6a53"
down_revision: str | Sequence[str] | None = "7f8be4fd9e68"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Scope, the partner's contact person and what payment counts from are no longer kept.
    op.execute(
        "DELETE FROM contract_field_values "
        "WHERE key IN ('scope', 'contact_person', 'payment_basis')"
    )


def downgrade() -> None:
    # The removed readings are gone; there is nothing to restore.
    pass
