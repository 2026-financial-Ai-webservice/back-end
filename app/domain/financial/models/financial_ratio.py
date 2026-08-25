# app/domain/financial/models/financial_ratio.py
import datetime

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FinancialRatio(Base):
    __tablename__ = "financial_ratios"

    financial_ratios_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    corp_code: Mapped[str] = mapped_column(
        String(8), ForeignKey("companies.corp_code"), nullable=False
    )
    business_year: Mapped[int] = mapped_column(Integer, nullable=False)
    report_code: Mapped[str] = mapped_column(String(5), default="11011")

    revenue: Mapped[int] = mapped_column(BigInteger, nullable=True)
    operating_income: Mapped[int] = mapped_column(BigInteger, nullable=True)
    net_income: Mapped[int] = mapped_column(BigInteger, nullable=True)
    total_liabilities: Mapped[int] = mapped_column(BigInteger, nullable=True)
    total_equity: Mapped[int] = mapped_column(BigInteger, nullable=True)
    operating_cash_flow: Mapped[int] = mapped_column(BigInteger, nullable=True)
    capex: Mapped[int] = mapped_column(BigInteger, nullable=True)
    interest_expense: Mapped[int] = mapped_column(BigInteger, nullable=True)
    fcf: Mapped[int] = mapped_column(BigInteger, nullable=True)
    depreciation: Mapped[int] = mapped_column(BigInteger, nullable=True)
    cash_and_equivalents: Mapped[int] = mapped_column(BigInteger, nullable=True)
    total_borrowings: Mapped[int] = mapped_column(BigInteger, nullable=True)

    roe: Mapped[float] = mapped_column(Numeric(12, 6), nullable=True)
    debt_ratio: Mapped[float] = mapped_column(Numeric(12, 6), nullable=True)
    interest_coverage: Mapped[float] = mapped_column(Numeric(12, 6), nullable=True)
    dps: Mapped[float] = mapped_column(Numeric(18, 4), nullable=True)  # 아래 참고

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("corp_code", "business_year", "report_code", name="uq_financial_ratio"),
    )