"""initial

Revision ID: 43adc2594315
Revises:
Create Date: 2026-11-26 09:00:28.496922

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "43adc2594315"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Partner search uses trigram indexes.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "contract_code_counters",
        sa.Column("prefix", sa.String(length=16), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("last_number", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("prefix", "year", name=op.f("pk_contract_code_counters")),
    )
    op.create_table(
        "document_files",
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=128), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_files")),
        sa.UniqueConstraint("sha256", name=op.f("uq_document_files_sha256")),
    )
    op.create_table(
        "partners",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("legal_name", sa.String(length=500), nullable=True),
        sa.Column("tax_code", sa.String(length=32), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=255), nullable=True),
        sa.Column("is_customer", sa.Boolean(), nullable=False),
        sa.Column("is_supplier", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("can_order_before_contract", sa.Boolean(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_partners")),
        sa.UniqueConstraint("code", name=op.f("uq_partners_code")),
    )
    op.create_index(
        "ix_partners_created_at_id",
        "partners",
        [sa.literal_column("created_at DESC"), sa.literal_column("id DESC")],
        unique=False,
    )
    op.create_index(
        "ix_partners_search_trgm",
        "partners",
        [
            sa.literal_column(
                "(lower(code || ' ' || name || ' ' || coalesce(legal_name, ''))) gin_trgm_ops"
            )
        ],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(op.f("ix_partners_tax_code"), "partners", ["tax_code"], unique=False)
    op.create_table(
        "seed_runs",
        sa.Column("step", sa.String(length=32), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("report", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_seed_runs")),
        sa.UniqueConstraint("step", name=op.f("uq_seed_runs_step")),
    )
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "roles", postgresql.ARRAY(sa.String(length=32)), server_default="{}", nullable=False
        ),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)
    op.create_index(
        "uq_users_email_lower", "users", [sa.literal_column("lower(email)")], unique=True
    )
    op.create_table(
        "document_sets",
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("partner_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"],
            ["partners.id"],
            name=op.f("fk_document_sets_partner_id_partners"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_sets")),
        sa.UniqueConstraint("source_path", name=op.f("uq_document_sets_source_path")),
    )
    op.create_index("ix_document_sets_partner_id", "document_sets", ["partner_id"], unique=False)
    op.create_table(
        "fuel_prices",
        sa.Column("fuel_type", sa.String(length=100), nullable=False),
        sa.Column("effective_on", sa.Date(), nullable=False),
        sa.Column("price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_fuel_prices_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fuel_prices")),
        sa.UniqueConstraint("fuel_type", "effective_on", name="uq_fuel_prices_type_date"),
    )
    op.create_index(
        "ix_fuel_prices_created_at_id",
        "fuel_prices",
        [sa.literal_column("created_at DESC"), sa.literal_column("id DESC")],
        unique=False,
    )
    op.create_table(
        "partner_conflicts",
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_id", sa.Uuid(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"],
            ["partners.id"],
            name=op.f("fk_partner_conflicts_partner_id_partners"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_id"],
            ["users.id"],
            name=op.f("fk_partner_conflicts_resolved_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_partner_conflicts")),
    )
    op.create_index(
        "ix_partner_conflicts_created_at_id",
        "partner_conflicts",
        [sa.literal_column("created_at DESC"), sa.literal_column("id DESC")],
        unique=False,
    )
    op.create_index(
        op.f("ix_partner_conflicts_partner_id"), "partner_conflicts", ["partner_id"], unique=False
    )
    op.create_index(
        "uq_partner_conflicts_open",
        "partner_conflicts",
        ["partner_id", "kind"],
        unique=True,
        postgresql_where=sa.text("resolved_at IS NULL"),
    )
    op.create_table(
        "partner_external_refs",
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("external_code", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"],
            ["partners.id"],
            name=op.f("fk_partner_external_refs_partner_id_partners"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_partner_external_refs")),
        sa.UniqueConstraint(
            "source", "external_code", name=op.f("uq_partner_external_refs_source")
        ),
    )
    op.create_index(
        op.f("ix_partner_external_refs_partner_id"),
        "partner_external_refs",
        ["partner_id"],
        unique=False,
    )
    op.create_table(
        "push_devices",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("locale", sa.String(length=8), server_default="en", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_push_devices_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_push_devices")),
        sa.UniqueConstraint("token", name=op.f("uq_push_devices_token")),
    )
    op.create_index(op.f("ix_push_devices_user_id"), "push_devices", ["user_id"], unique=False)
    op.create_table(
        "contracts",
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=True),
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("replaced_by_id", sa.Uuid(), nullable=True),
        sa.Column("replaced_on", sa.Date(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.String(length=255), nullable=True),
        sa.Column("signed_on", sa.Date(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("end_on", sa.Date(), nullable=True),
        sa.Column("notice_on", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("missing_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_contracts_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_id"],
            ["document_sets.id"],
            name=op.f("fk_contracts_dossier_id_document_sets"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"],
            ["partners.id"],
            name=op.f("fk_contracts_partner_id_partners"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by_id"],
            ["contracts.id"],
            name=op.f("fk_contracts_replaced_by_id_contracts"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contracts")),
    )
    op.create_index("ix_contracts_code", "contracts", ["code"], unique=True)
    op.create_index(
        "ix_contracts_created_at_id",
        "contracts",
        [sa.literal_column("created_at DESC"), sa.literal_column("id DESC")],
        unique=False,
    )
    op.create_index("ix_contracts_dossier_id", "contracts", ["dossier_id"], unique=False)
    op.create_index("ix_contracts_effective_from", "contracts", ["effective_from"], unique=False)
    op.create_index("ix_contracts_end_on", "contracts", ["end_on"], unique=False)
    op.create_index("ix_contracts_missing_count", "contracts", ["missing_count"], unique=False)
    op.create_index("ix_contracts_notice_on", "contracts", ["notice_on"], unique=False)
    op.create_index("ix_contracts_partner_id", "contracts", ["partner_id"], unique=False)
    op.create_index("ix_contracts_signed_on", "contracts", ["signed_on"], unique=False)
    op.create_index("ix_contracts_status", "contracts", ["status"], unique=False)
    op.create_table(
        "document_set_files",
        sa.Column("set_id", sa.Uuid(), nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["document_files.id"],
            name=op.f("fk_document_set_files_file_id_document_files"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["set_id"],
            ["document_sets.id"],
            name=op.f("fk_document_set_files_set_id_document_sets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_set_files")),
        sa.UniqueConstraint("set_id", "path", name=op.f("uq_document_set_files_set_id")),
    )
    op.create_index(
        "ix_document_set_files_file_id", "document_set_files", ["file_id"], unique=False
    )
    op.create_table(
        "contract_instruments",
        sa.Column("contract_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("code", sa.String(length=48), nullable=True),
        sa.Column("review_state", sa.String(length=16), nullable=True),
        sa.Column("signing_state", sa.String(length=16), server_default="signed", nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["contracts.id"],
            name=op.f("fk_contract_instruments_contract_id_contracts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_contract_instruments_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["document_files.id"],
            name=op.f("fk_contract_instruments_file_id_document_files"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contract_instruments")),
    )
    op.create_index("ix_contract_instruments_code", "contract_instruments", ["code"], unique=True)
    op.create_index(
        "ix_contract_instruments_contract_id", "contract_instruments", ["contract_id"], unique=False
    )
    op.create_index(
        "ix_contract_instruments_review_state",
        "contract_instruments",
        ["review_state"],
        unique=False,
    )
    op.create_table(
        "contract_events",
        sa.Column("contract_id", sa.Uuid(), nullable=False),
        sa.Column("instrument_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("signing_state", sa.String(length=16), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name=op.f("fk_contract_events_actor_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["contracts.id"],
            name=op.f("fk_contract_events_contract_id_contracts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["document_files.id"],
            name=op.f("fk_contract_events_file_id_document_files"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["contract_instruments.id"],
            name=op.f("fk_contract_events_instrument_id_contract_instruments"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contract_events")),
    )
    op.create_index(
        "ix_contract_events_contract_id",
        "contract_events",
        ["contract_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "contract_field_values",
        sa.Column("instrument_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("entered_by_id", sa.Uuid(), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["entered_by_id"],
            ["users.id"],
            name=op.f("fk_contract_field_values_entered_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["contract_instruments.id"],
            name=op.f("fk_contract_field_values_instrument_id_contract_instruments"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contract_field_values")),
    )
    op.create_index(
        "ix_contract_field_values_instrument_key",
        "contract_field_values",
        ["instrument_id", "key"],
        unique=False,
    )
    op.create_index(
        "uq_contract_field_values_current",
        "contract_field_values",
        ["instrument_id", "key"],
        unique=True,
        postgresql_where=sa.text("superseded_at IS NULL"),
    )
    op.create_table(
        "fuel_clauses",
        sa.Column("contract_id", sa.Uuid(), nullable=False),
        sa.Column("instrument_id", sa.Uuid(), nullable=False),
        sa.Column("fuel_type", sa.String(length=100), nullable=False),
        sa.Column("base_price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("base_on", sa.Date(), nullable=False),
        sa.Column("share", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("threshold", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("lag_days", sa.Integer(), nullable=False),
        sa.Column("rounding", sa.String(length=16), nullable=False),
        sa.Column("is_cumulative", sa.Boolean(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_by_id", sa.Uuid(), nullable=True),
        sa.Column("withdraw_reason", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["contracts.id"],
            name=op.f("fk_fuel_clauses_contract_id_contracts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_fuel_clauses_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["contract_instruments.id"],
            name=op.f("fk_fuel_clauses_instrument_id_contract_instruments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["withdrawn_by_id"],
            ["users.id"],
            name=op.f("fk_fuel_clauses_withdrawn_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fuel_clauses")),
    )
    op.create_index("ix_fuel_clauses_contract_id", "fuel_clauses", ["contract_id"], unique=False)
    op.create_table(
        "price_tables",
        sa.Column("contract_id", sa.Uuid(), nullable=False),
        sa.Column("instrument_id", sa.Uuid(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_by_id", sa.Uuid(), nullable=True),
        sa.Column("withdraw_reason", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["contracts.id"],
            name=op.f("fk_price_tables_contract_id_contracts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_price_tables_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["contract_instruments.id"],
            name=op.f("fk_price_tables_instrument_id_contract_instruments"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["withdrawn_by_id"],
            ["users.id"],
            name=op.f("fk_price_tables_withdrawn_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_price_tables")),
    )
    op.create_index("ix_price_tables_contract_id", "price_tables", ["contract_id"], unique=False)
    op.create_table(
        "price_lines",
        sa.Column("table_id", sa.Uuid(), nullable=False),
        sa.Column("service", sa.String(length=200), nullable=False),
        sa.Column("origin", sa.String(length=200), nullable=True),
        sa.Column("destination", sa.String(length=200), nullable=True),
        sa.Column("vehicle", sa.String(length=100), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("includes_vat", sa.Boolean(), nullable=True),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_by_id", sa.Uuid(), nullable=True),
        sa.Column("withdraw_reason", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("fk_price_lines_created_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["table_id"],
            ["price_tables.id"],
            name=op.f("fk_price_lines_table_id_price_tables"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["withdrawn_by_id"],
            ["users.id"],
            name=op.f("fk_price_lines_withdrawn_by_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_price_lines")),
    )
    op.create_index("ix_price_lines_table_id", "price_lines", ["table_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_price_lines_table_id", table_name="price_lines")
    op.drop_table("price_lines")
    op.drop_index("ix_price_tables_contract_id", table_name="price_tables")
    op.drop_table("price_tables")
    op.drop_index("ix_fuel_clauses_contract_id", table_name="fuel_clauses")
    op.drop_table("fuel_clauses")
    op.drop_index(
        "uq_contract_field_values_current",
        table_name="contract_field_values",
        postgresql_where=sa.text("superseded_at IS NULL"),
    )
    op.drop_index("ix_contract_field_values_instrument_key", table_name="contract_field_values")
    op.drop_table("contract_field_values")
    op.drop_index("ix_contract_events_contract_id", table_name="contract_events")
    op.drop_table("contract_events")
    op.drop_index("ix_contract_instruments_review_state", table_name="contract_instruments")
    op.drop_index("ix_contract_instruments_contract_id", table_name="contract_instruments")
    op.drop_index("ix_contract_instruments_code", table_name="contract_instruments")
    op.drop_table("contract_instruments")
    op.drop_index("ix_document_set_files_file_id", table_name="document_set_files")
    op.drop_table("document_set_files")
    op.drop_index("ix_contracts_status", table_name="contracts")
    op.drop_index("ix_contracts_signed_on", table_name="contracts")
    op.drop_index("ix_contracts_partner_id", table_name="contracts")
    op.drop_index("ix_contracts_notice_on", table_name="contracts")
    op.drop_index("ix_contracts_missing_count", table_name="contracts")
    op.drop_index("ix_contracts_end_on", table_name="contracts")
    op.drop_index("ix_contracts_effective_from", table_name="contracts")
    op.drop_index("ix_contracts_dossier_id", table_name="contracts")
    op.drop_index("ix_contracts_created_at_id", table_name="contracts")
    op.drop_index("ix_contracts_code", table_name="contracts")
    op.drop_table("contracts")
    op.drop_index(op.f("ix_push_devices_user_id"), table_name="push_devices")
    op.drop_table("push_devices")
    op.drop_index(op.f("ix_partner_external_refs_partner_id"), table_name="partner_external_refs")
    op.drop_table("partner_external_refs")
    op.drop_index(
        "uq_partner_conflicts_open",
        table_name="partner_conflicts",
        postgresql_where=sa.text("resolved_at IS NULL"),
    )
    op.drop_index(op.f("ix_partner_conflicts_partner_id"), table_name="partner_conflicts")
    op.drop_index("ix_partner_conflicts_created_at_id", table_name="partner_conflicts")
    op.drop_table("partner_conflicts")
    op.drop_index("ix_fuel_prices_created_at_id", table_name="fuel_prices")
    op.drop_table("fuel_prices")
    op.drop_index("ix_document_sets_partner_id", table_name="document_sets")
    op.drop_table("document_sets")
    op.drop_index("uq_users_email_lower", table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_table("seed_runs")
    op.drop_index(op.f("ix_partners_tax_code"), table_name="partners")
    op.drop_index("ix_partners_search_trgm", table_name="partners", postgresql_using="gin")
    op.drop_index("ix_partners_created_at_id", table_name="partners")
    op.drop_table("partners")
    op.drop_table("document_files")
    op.drop_table("contract_code_counters")
