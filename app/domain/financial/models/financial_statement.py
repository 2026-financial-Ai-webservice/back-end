import datetime
from sqlalchemy import String, SmallInteger, BigInteger, Numeric, Text, UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import func, TIMESTAMP
from app.core.database import Base

class FinancialStatement(Base):
    __tablename__ = "financial_statements"

    financial_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    corp_code: Mapped[str] = mapped_column(String(8), ForeignKey("companies.corp_code"), nullable=False)
    business_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    report_code: Mapped[str] = mapped_column(String(5), nullable=False)
    statement_scope: Mapped[str] = mapped_column(String(10), nullable=False)  # 연결/별도
    statement_type: Mapped[str] = mapped_column(String(20), nullable=True)     # BS/IS/CF...
    account_id: Mapped[str] = mapped_column(Text, nullable=True)
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)
    current_amount: Mapped[float] = mapped_column(Numeric(24, 2), nullable=True)
    receipt_no: Mapped[str] = mapped_column(String(20), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "corp_code", "business_year", "report_code",
            "statement_scope", "statement_type", "account_id",
            name="uq_financial_statement",
        ),
    )