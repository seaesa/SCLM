"""cancel contract documents

Revision ID: ec516b4e7202
Revises: 75ceaab251c0
Create Date: 2026-11-26 13:43:17.640286

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ec516b4e7202"
down_revision: str | Sequence[str] | None = "75ceaab251c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "contract_instruments",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        if_not_exists=True,
    )
    op.add_column(
        "contract_instruments",
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        if_not_exists=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "-- squawk-ignore ban-drop-column\nALTER TABLE contract_instruments DROP COLUMN cancel_reason"
    )
    op.execute(
        "-- squawk-ignore ban-drop-column\nALTER TABLE contract_instruments DROP COLUMN cancelled_at"
    )
