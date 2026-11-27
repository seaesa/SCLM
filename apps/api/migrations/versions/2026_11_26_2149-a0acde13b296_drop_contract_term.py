"""drop contract term

Revision ID: a0acde13b296
Revises: 00f135a1f1fa
Create Date: 2026-11-26 21:49:32.777399

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a0acde13b296"
down_revision: str | Sequence[str] | None = "00f135a1f1fa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # An empty end date already means the contract has no end; the term choice is gone.
    op.execute("DELETE FROM contract_field_values WHERE key = 'term'")


def downgrade() -> None:
    """Nothing to restore: the choice only restated whether an end date was entered."""
