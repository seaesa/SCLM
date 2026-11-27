"""partner owner and addenda list

Revision ID: 9d5bf240c51a
Revises: 43adc2594315
Create Date: 2026-11-26 09:57:04.057356

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9d5bf240c51a"
down_revision: str | Sequence[str] | None = "43adc2594315"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_INSTRUMENT_COLUMNS = (
    ("number", sa.String(length=128)),
    ("signed_on", sa.Date()),
    ("effective_from", sa.Date()),
    ("effective_to", sa.Date()),
    ("adjustments", sa.String(length=128)),
    ("summary", sa.Text()),
)


def upgrade() -> None:
    # Instrument columns are copies of current values, filled by `refresh-contracts` (or
    # nightly); partners start with no owner.
    for name, type_ in _INSTRUMENT_COLUMNS:
        op.add_column(
            "contract_instruments", sa.Column(name, type_, nullable=True), if_not_exists=True
        )
    op.add_column("partners", sa.Column("owner_id", sa.Uuid(), nullable=True), if_not_exists=True)
    op.execute(
        "-- squawk-ignore adding-foreign-key-constraint,constraint-missing-not-valid,prefer-robust-stmts\n"
        "ALTER TABLE partners ADD CONSTRAINT fk_partners_owner_id_users "
        "FOREIGN KEY (owner_id) REFERENCES users (id) ON DELETE SET NULL"
    )
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_contract_instruments_effective_from",
            "contract_instruments",
            ["effective_from"],
            postgresql_concurrently=True,
            if_not_exists=True,
        )
        op.create_index(
            "ix_partners_owner_id",
            "partners",
            ["owner_id"],
            postgresql_concurrently=True,
            if_not_exists=True,
        )


def downgrade() -> None:
    op.drop_constraint("fk_partners_owner_id_users", "partners", type_="foreignkey")
    op.drop_index("ix_partners_owner_id", table_name="partners")
    op.drop_column("partners", "owner_id")
    op.drop_index("ix_contract_instruments_effective_from", table_name="contract_instruments")
    for name, _ in reversed(_INSTRUMENT_COLUMNS):
        op.drop_column("contract_instruments", name)
