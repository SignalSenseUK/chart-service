"""initial charts table

Revision ID: 0001_initial_charts
Revises:
Create Date: 2026-05-15

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0001_initial_charts"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "charts",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("chart_definition", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("inline_series", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_rendered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "source_kind in ('direct','eodhd','ib')",
            name="ck_charts_source_kind",
        ),
    )

    op.create_index(
        "idx_charts_created_at",
        "charts",
        [sa.text("created_at DESC")],
    )
    op.create_index("idx_charts_source_kind", "charts", ["source_kind"])
    op.create_index(
        "idx_charts_chart_definition_gin",
        "charts",
        ["chart_definition"],
        postgresql_using="gin",
    )
    op.create_index(
        "idx_charts_deleted_at",
        "charts",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_charts_deleted_at", table_name="charts")
    op.drop_index("idx_charts_chart_definition_gin", table_name="charts")
    op.drop_index("idx_charts_source_kind", table_name="charts")
    op.drop_index("idx_charts_created_at", table_name="charts")
    op.drop_table("charts")
