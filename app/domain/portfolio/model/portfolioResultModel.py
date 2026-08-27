import datetime
from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
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
    # 요청 파라미터 스냅샷 (요청 내용 보존)
    seed_money: Mapped[int] = mapped_column(BigInteger, nullable=False)
    investment_period: Mapped[str] = mapped_column(String(30), nullable=False)
    risk_preference: Mapped[str] = mapped_column(String(30), nullable=False)
    return_preference: Mapped[str] = mapped_column(String(30), nullable=False)
    valuation_preference: Mapped[str] = mapped_column(String(30), nullable=False)

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
    companies: Mapped[list["PortfolioResultCompany"]] = relationship(
        back_populates="portfolio_result", cascade="all, delete-orphan"
    )