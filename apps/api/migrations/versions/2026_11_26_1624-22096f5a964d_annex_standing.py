"""annex standing

Revision ID: 22096f5a964d
Revises: 7c827f8c6a53
Create Date: 2026-11-26 16:24:29.717667

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "22096f5a964d"
down_revision: str | Sequence[str] | None = "7c827f8c6a53"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLE = "contract_instruments"
_FK = "fk_contract_instruments_replaced_by_id_contract_instruments"


def upgrade() -> None:
    """Annexes carry a computed standing; cancelling a document is gone."""
    op.add_column(
        _TABLE, sa.Column("standing", sa.String(length=16), nullable=True), if_not_exists=True
    )
    op.add_column(_TABLE, sa.Column("replaced_by_id", sa.Uuid(), nullable=True), if_not_exists=True)
    op.execute(
        "-- squawk-ignore adding-foreign-key-constraint,constraint-missing-not-valid,prefer-robust-stmts\n"
        f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_FK} FOREIGN KEY (replaced_by_id) "
        f"REFERENCES {_TABLE} (id) ON DELETE SET NULL"
    )
    for column in ("cancel_reason", "is_current", "cancelled_at"):
        op.execute(
            f"-- squawk-ignore ban-drop-column\nALTER TABLE {_TABLE} DROP COLUMN IF EXISTS {column}"
        )


def downgrade() -> None:
    op.add_column(_TABLE, sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        _TABLE,
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(_TABLE, sa.Column("cancel_reason", sa.Text(), nullable=True))
    op.drop_constraint(_FK, _TABLE, type_="foreignkey")
    op.execute(f"-- squawk-ignore ban-drop-column\nALTER TABLE {_TABLE} DROP COLUMN replaced_by_id")
    op.execute(f"-- squawk-ignore ban-drop-column\nALTER TABLE {_TABLE} DROP COLUMN standing")
