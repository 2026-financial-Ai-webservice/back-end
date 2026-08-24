"""Create the market_data table.

Revision ID: 51f5feaf4558
Revises:
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260824_01"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_data",
        sa.Column(
            "corp_code",
            sa.String(length=8),
            sa.ForeignKey("companies.corp_code", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("market_date", sa.Date(), nullable=False),
        sa.Column("current_price", sa.BigInteger(), nullable=True),
        sa.Column("listed_shares", sa.BigInteger(), nullable=True),
        sa.Column("market_cap", sa.BigInteger(), nullable=True),
        sa.Column("per", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("pbr", sa.Numeric(precision=20, scale=2), nullable=True),
        sa.Column("eps", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("bps", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.PrimaryKeyConstraint(
            "corp_code",
            "market_date",
            name="pk_market_data",
        ),
    )

    op.create_index(
        "ix_market_data_market_date",
        "market_data",
        ["market_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_market_data_market_date",
        table_name="market_data",
    )
    op.drop_table("market_data")