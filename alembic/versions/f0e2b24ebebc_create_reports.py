"""create company_reports and report_chunks

Revision ID: f0e2b24ebebc
Revises: 51f5feaf4558
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector


revision: str = "f0e2b24ebebc"
down_revision: str | None = "b7d9c2a04f31"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # VECTOR(1536) 컬럼을 사용하기 위해 필요
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "company_reports",
        sa.Column(
            "report_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "corp_code",
            sa.String(length=8),
            sa.ForeignKey("companies.corp_code"),
            nullable=False,
        ),
        sa.Column(
            "receipt_no",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "report_name",
            sa.String(length=300),
            nullable=False,
        ),
        sa.Column(
            "filing_date",
            sa.Date(),
            nullable=True,
        ),
        sa.Column(
            "business_year",
            sa.SmallInteger(),
            nullable=False,
        ),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "receipt_no",
            name="uq_company_reports_receipt_no",
        ),
    )

    op.create_table(
        "report_chunks",
        sa.Column(
            "chunk_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "report_id",
            sa.BigInteger(),
            sa.ForeignKey(
                "company_reports.report_id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "major_section",
            sa.String(length=200),
            nullable=True,
        ),
        sa.Column(
            "minor_section",
            sa.String(length=300),
            nullable=True,
        ),
        sa.Column(
            "chunk_order",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "embedding",
            Vector(1536),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "report_id",
            "major_section",
            "minor_section",
            "chunk_order",
            name="uq_report_chunk_order",
        ),
    )


def downgrade() -> None:
    # FK 때문에 자식 테이블부터 제거
    op.drop_table("report_chunks")
    op.drop_table("company_reports")

    # vector extension은 다른 테이블도 사용할 수 있으므로 삭제하지 않음