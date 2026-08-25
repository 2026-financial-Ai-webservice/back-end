"""create market_data table

Revision ID: b7d9c2a04f31
Revises: e765bce596ac
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7d9c2a04f31"
down_revision: str | Sequence[str] | None = "e765bce596ac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_data",
        sa.Column("corp_code", sa.String(length=8), nullable=False),
        sa.Column("market_date", sa.Date(), nullable=False),
        sa.Column("current_price", sa.BigInteger(), nullable=True),
        sa.Column("listed_shares", sa.BigInteger(), nullable=True),
        sa.Column("market_cap", sa.BigInteger(), nullable=True),
        sa.Column("per", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("pbr", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("eps", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column("bps", sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["corp_code"], ["companies.corp_code"]),
        sa.PrimaryKeyConstraint("corp_code", "market_date"),
    )


def downgrade() -> None:
    op.drop_table("market_data")
