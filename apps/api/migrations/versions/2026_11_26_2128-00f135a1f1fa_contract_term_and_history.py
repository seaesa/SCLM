"""contract term and history

Revision ID: 00f135a1f1fa
Revises: 513fd8a638d4
Create Date: 2026-11-26 21:28:29.964202

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "00f135a1f1fa"
down_revision: str | Sequence[str] | None = "513fd8a638d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_FK = "fk_contract_events_instrument_id_contract_instruments"


def _point_events_at_instruments(ondelete: str) -> None:
    op.execute(
        "-- squawk-ignore ban-drop-constraint,adding-foreign-key-constraint,"
        "constraint-missing-not-valid,prefer-robust-stmts\n"
        f"ALTER TABLE contract_events DROP CONSTRAINT {_FK}, "
        f"ADD CONSTRAINT {_FK} FOREIGN KEY (instrument_id) "
        f"REFERENCES contract_instruments (id) ON DELETE {ondelete}"
    )


def upgrade() -> None:
    op.add_column(
        "contract_events",
        sa.Column("instrument_code", sa.String(length=64), nullable=True),
        if_not_exists=True,
    )
    op.add_column(
        "contract_events",
        sa.Column("changes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        if_not_exists=True,
    )
    # Events outlive their document, so a deletion still shows in the history.
    _point_events_at_instruments("SET NULL")
    op.execute(
        "UPDATE contract_events e SET instrument_code = i.code "
        "FROM contract_instruments i WHERE i.id = e.instrument_id"
    )
    # A deleted document's code used to be kept in the comment.
    op.execute(
        "UPDATE contract_events SET instrument_code = comment, comment = NULL "
        "WHERE kind = 'deleted' AND instrument_code IS NULL"
    )
    # The "not stated by the document" marker is gone: a term is now fixed or indefinite.
    op.execute("DELETE FROM contract_field_values WHERE key = 'unstated'")


def downgrade() -> None:
    _point_events_at_instruments("CASCADE")
    op.execute(
        "-- squawk-ignore ban-drop-column\n"
        "ALTER TABLE contract_events DROP COLUMN IF EXISTS changes, "
        "DROP COLUMN IF EXISTS instrument_code"
    )
