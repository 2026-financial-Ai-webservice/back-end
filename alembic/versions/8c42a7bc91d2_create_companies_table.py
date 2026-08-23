"""create companies table

Revision ID: 8c42a7bc91d2
Revises: d5c653b2ffcf
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8c42a7bc91d2"
down_revision: str | None = "d5c653b2ffcf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("corp_code", sa.String(length=8), nullable=False),
        sa.Column("stock_code", sa.String(length=6), nullable=True),
        sa.Column("corp_name", sa.String(length=100), nullable=False),
        sa.Column("industry_category", sa.String(length=255), nullable=True),
        sa.Column("industry_code", sa.String(length=10), nullable=True),
        sa.Column(
            "is_manufacturing",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("corp_code"),
        sa.UniqueConstraint("stock_code"),
    )


def downgrade() -> None:
    op.drop_table("companies")
