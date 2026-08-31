"""add fundamental_screening table

Revision ID: 8f74b922efcf
Revises: f0e2b24ebebc
Create Date: 2026-08-25 18:47:30.205555

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8f74b922efcf'
down_revision: str | Sequence[str] | None = 'f0e2b24ebebc'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('fundamental_screening',
        sa.Column('financial_screening_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('corp_code', sa.String(length=8), nullable=False),
        sa.Column('business_year', sa.Integer(), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('fail_reasons', sa.Text(), nullable=True),
        sa.Column(
            'screened_at', sa.TIMESTAMP(timezone=True),
            server_default=sa.text('now()'), nullable=False
        ),
        sa.ForeignKeyConstraint(['corp_code'], ['companies.corp_code'], ),
        sa.PrimaryKeyConstraint('financial_screening_id'),
        sa.UniqueConstraint('corp_code', name='uq_fundamental_screening_corp_code')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('fundamental_screening')
