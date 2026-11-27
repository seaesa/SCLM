"""Mark contracts loaded from the archive and the events that loaded them.

Revision ID: 513fd8a638d4
Revises: 22096f5a964d
Create Date: 2026-11-26 17:18:33.572262

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "513fd8a638d4"
down_revision: str | Sequence[str] | None = "22096f5a964d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "contracts",
        sa.Column("is_imported", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        if_not_exists=True,
    )
    # Archive dossiers are named "archive/<key>" by the seed.
    op.execute(
        "UPDATE contracts SET is_imported = true FROM document_sets "
        "WHERE document_sets.id = contracts.dossier_id "
        "AND document_sets.source_path LIKE 'archive/%'"
    )
    op.execute(
        "UPDATE contract_events SET kind = 'imported' FROM contracts "
        "WHERE contracts.id = contract_events.contract_id "
        "AND contracts.is_imported AND contract_events.kind = 'created'"
    )


def downgrade() -> None:
    op.execute("UPDATE contract_events SET kind = 'created' WHERE kind = 'imported'")
    op.execute(
        "-- squawk-ignore ban-drop-column\nALTER TABLE contracts DROP COLUMN IF EXISTS is_imported"
    )
