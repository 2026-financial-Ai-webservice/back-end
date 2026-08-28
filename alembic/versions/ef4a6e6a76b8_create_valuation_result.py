"""create valuation result

Revision ID: ef4a6e6a76b8
Revises: 8f74b922efcf
Create Date: 2026-08-28 21:05:41.523604

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ef4a6e6a76b8'
down_revision: Union[str, Sequence[str], None] = '8f74b922efcf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.create_table(
        "valuation_result",

        sa.Column(
            "valuation_result_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),

        sa.Column(
            "request_id",
            sa.BigInteger(),
            nullable=False,
        ),

        sa.Column(
            "corp_code",
            sa.String(length=8),
            nullable=False,
        ),

        sa.Column(
            "business_year",
            sa.Integer(),
            nullable=False,
        ),

        # 가중치 적용 후 개별 점수
        sa.Column(
            "dcf",
            sa.Numeric(precision=10, scale=4),
            nullable=False,
        ),

        sa.Column(
            "per",
            sa.Numeric(precision=10, scale=4),
            nullable=False,
        ),

        sa.Column(
            "dividend",
            sa.Numeric(precision=10, scale=4),
            nullable=False,
        ),

        # 세 개별 점수의 합
        sa.Column(
            "score",
            sa.Numeric(precision=10, scale=4),
            nullable=False,
        ),

        sa.Column(
            "rank_position",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),

        sa.PrimaryKeyConstraint(
            "valuation_result_id",
            name="pk_valuation_result",
        ),

        sa.ForeignKeyConstraint(
            ["request_id"],
            ["portfolio_request.request_id"],
            name="fk_valuation_result_request",
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["corp_code"],
            ["companies.corp_code"],
            name="fk_valuation_result_company",
        ),

        sa.CheckConstraint(
            "rank_position > 0",
            name="ck_valuation_result_rank_position_positive",
        ),

        sa.UniqueConstraint(
            "request_id",
            "corp_code",
            name="uq_valuation_result_request_company",
        ),
    )


def downgrade() -> None:
    op.drop_table("valuation_result")