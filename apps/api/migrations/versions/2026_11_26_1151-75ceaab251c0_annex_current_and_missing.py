"""annex current and missing

Revision ID: 75ceaab251c0
Revises: 9d5bf240c51a
Create Date: 2026-11-26 11:51:17.548402

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "75ceaab251c0"
down_revision: str | Sequence[str] | None = "9d5bf240c51a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema. Run `app.cli refresh-contracts` afterwards to fill both columns."""
    op.add_column(
        "contract_instruments",
        sa.Column("missing_count", sa.Integer(), server_default="0", nullable=False),
        if_not_exists=True,
    )
    op.add_column(
        "contract_instruments",
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        if_not_exists=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("contract_instruments", "is_current")
    op.drop_column("contract_instruments", "missing_count")
