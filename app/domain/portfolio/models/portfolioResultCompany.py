
from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PortfolioResultCompany(Base):
    __tablename__ = "portfolio_result_companies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    portfolio_result_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("portfolio_results.portfolio_result_id"), nullable=False
    )
    corp_code: Mapped[str] = mapped_column(
        String(8), ForeignKey("companies.corp_code"), nullable=False
    )
    company_name: Mapped[str] = mapped_column(String(100), nullable=False)
    allocated_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    final_score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    allocation_ratio: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    rank_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    per: Mapped[float] = mapped_column(Numeric(8, 2), nullable=True)
    roe: Mapped[float] = mapped_column(Numeric(8, 2), nullable=True)
    dcf: Mapped[float] = mapped_column(Numeric(8, 2), nullable=True)
    investment_reason: Mapped[str] = mapped_column(Text, nullable=True)
    portfolio_result: Mapped["PortfolioResult"] = relationship(back_populates="companies")  # noqa: F821