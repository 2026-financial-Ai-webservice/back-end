"""create company reports and report chunks

Revision ID: 3062dc20a1aa
Revises: b7d9c2a04f31
Create Date: 2026-08-24 16:06:50.486383

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3062dc20a1aa'
down_revision: Union[str, Sequence[str], None] = 'b7d9c2a04f31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "company_reports",
        sa.Column("report_id", sa.BigInteger(), primary_key=True),
        sa.Column("corp_code", sa.String(length=8), nullable=False),
        sa.Column("receipt_no", sa.String(length=14), nullable=False),
        sa.Column("report_name", sa.String(length=255), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=False),
        sa.Column("business_year", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["corp_code"],
            ["companies.corp_code"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "receipt_no",
            name="uq_company_reports_receipt_no",
        ),
    )

    op.create_index(
        "ix_company_reports_corp_code_business_year",
        "company_reports",
        ["corp_code", "business_year"],
    )

    op.create_table(
        "report_chunks",
        sa.Column("chunk_id", sa.BigInteger(), primary_key=True),
        sa.Column("report_id", sa.BigInteger(), nullable=False),
        sa.Column("major_section", sa.Text(), nullable=True),
        sa.Column("minor_section", sa.Text(), nullable=True),
        sa.Column("chunk_order", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["company_reports.report_id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "report_id",
            "chunk_order",
            name="uq_report_chunks_report_order",
        ),
    )

    op.create_index(
        "ix_report_chunks_report_id",
        "report_chunks",
        ["report_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_report_chunks_report_id",
        table_name="report_chunks",
    )
    op.drop_table("report_chunks")

    op.drop_index(
        "ix_company_reports_corp_code_business_year",
        table_name="company_reports",
    )
    op.drop_table("company_reports")