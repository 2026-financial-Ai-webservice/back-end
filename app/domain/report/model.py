from __future__ import annotations

from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CompanyReport(Base):
    __tablename__ = "company_reports"

    report_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    corp_code: Mapped[str] = mapped_column(
        String(8), ForeignKey("companies.corp_code"), nullable=False
    )
    receipt_no: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    report_name: Mapped[str] = mapped_column(String(300), nullable=False)
    filing_date: Mapped[date] = mapped_column(Date, nullable=False)
    business_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    chunks: Mapped[list[ReportChunk]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class ReportChunk(Base):
    __tablename__ = "report_chunks"

    chunk_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("company_reports.report_id", ondelete="CASCADE"), nullable=False
    )
    major_section: Mapped[str | None] = mapped_column(String(200))
    minor_section: Mapped[str | None] = mapped_column(String(300))
    chunk_order: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))

    report: Mapped[CompanyReport] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint(
            "report_id", "major_section", "minor_section", "chunk_order",
            name="uq_report_chunk_order",
        ),
    )
