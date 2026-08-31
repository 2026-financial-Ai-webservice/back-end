import datetime

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PortfolioResult(Base):
    __tablename__ = "portfolio_results"

    portfolio_result_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    request_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("portfolio_request.request_id"), nullable=False
    )

    # 집계 분석 결과
    total_investment: Mapped[int] = mapped_column(BigInteger, nullable=False)
    average_dividend_yield: Mapped[float] = mapped_column(Numeric(8, 4), nullable=True)
    average_dcf_upside: Mapped[float] = mapped_column(Numeric(8, 4), nullable=True)
    valuation_analysis: Mapped[str] = mapped_column(Text, nullable=True)
    market_indicator_analysis: Mapped[str] = mapped_column(Text, nullable=True)
    allocation_analysis: Mapped[str] = mapped_column(Text, nullable=True)
    share_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    companies: Mapped[list["PortfolioResultCompany"]] = relationship(   # noqa: F821
        back_populates="portfolio_result", cascade="all, delete-orphan"
    )