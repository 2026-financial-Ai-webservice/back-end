"""create portfolio request

Revision ID: 9aacba99bed0
Revises: ef4a6e6a76b8
Create Date: 2026-08-28 22:27:30.533999

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9aacba99bed0'
down_revision: str | Sequence[str] | None = 'ef4a6e6a76b8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None



def upgrade() -> None:
    op.create_table(
        "portfolio_request",
        sa.Column(
            "request_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            primary_key=True,
        ),
        sa.Column(
            "seed_money",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "investment_period",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "risk_preference",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "return_preference",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "valuation_preference",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "seed_money > 0",
            name="ck_portfolio_request_seed_money_positive",
        ),
        sa.CheckConstraint(
            """
            investment_period IN (
                'UNDER_1_YEAR',
                'ONE_TO_THREE_YEARS',
                'OVER_3_YEARS'
            )
            """,
            name="ck_portfolio_request_investment_period",
        ),
        sa.CheckConstraint(
            "risk_preference IN ('STABLE', 'AGGRESSIVE')",
            name="ck_portfolio_request_risk_preference",
        ),
        sa.CheckConstraint(
            "return_preference IN ('DIVIDEND', 'CAPITAL_GAIN')",
            name="ck_portfolio_request_return_preference",
        ),
        sa.CheckConstraint(
            """
            valuation_preference IN (
                'CURRENT_ASSET',
                'FUTURE_EARNINGS'
            )
            """,
            name="ck_portfolio_request_valuation_preference",
        ),
    )


def downgrade() -> None:
    op.drop_table("portfolio_request")