"""contract renewal and resigning

Revision ID: 7f8be4fd9e68
Revises: ec516b4e7202
Create Date: 2026-11-26 14:14:54.620521

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7f8be4fd9e68"
down_revision: str | Sequence[str] | None = "ec516b4e7202"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """The renewal clause, copied for filtering; re-signed contracts found from the newer one."""
    op.add_column(
        "contracts", sa.Column("renewal", sa.String(length=16), nullable=True), if_not_exists=True
    )
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_contracts_renewal",
            "contracts",
            ["renewal"],
            postgresql_concurrently=True,
            if_not_exists=True,
        )
        op.create_index(
            "ix_contracts_replaced_by_id",
            "contracts",
            ["replaced_by_id"],
            postgresql_concurrently=True,
            if_not_exists=True,
        )
    # `app.cli refresh-contracts` fills `renewal` from the recorded facts.


def downgrade() -> None:
    op.drop_index("ix_contracts_replaced_by_id", table_name="contracts")
    op.drop_index("ix_contracts_renewal", table_name="contracts")
    op.execute("-- squawk-ignore ban-drop-column\nALTER TABLE contracts DROP COLUMN renewal")
