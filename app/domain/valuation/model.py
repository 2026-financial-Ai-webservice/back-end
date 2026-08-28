from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ValuationResult(Base):
    __tablename__ = "valuation_result"

    valuation_result_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    request_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "portfolio_request.request_id",
            name="fk_valuation_result_request",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    corp_code: Mapped[str] = mapped_column(
        String(8),
        ForeignKey(
            "companies.corp_code",
            name="fk_valuation_result_company",
        ),
        nullable=False,
    )
    business_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    dcf: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,
    )

    per: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,
    )

    dividend: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,
    )

    score: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,
    )

    rank_position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "rank_position > 0",
            name="ck_valuation_result_rank_position_positive",
        ),
        UniqueConstraint(
            "request_id",
            "corp_code",
            name="uq_valuation_result_request_company",
        ),
    )

class PortfolioRequest(Base):
    __tablename__ = "portfolio_request"

    request_id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    seed_money: Mapped[int] = mapped_column(BigInteger, nullable=False)
    investment_period: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_preference: Mapped[str] = mapped_column(String(20), nullable=False)
    return_preference: Mapped[str] = mapped_column(String(20), nullable=False)
    valuation_preference: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "seed_money > 0", name="ck_portfolio_request_seed_money_positive"
        ),
        CheckConstraint(
            "investment_period IN ('UNDER_1_YEAR', 'ONE_TO_THREE_YEARS', 'OVER_3_YEARS')",
            name="ck_portfolio_request_investment_period",
        ),
        CheckConstraint(
            "risk_preference IN ('STABLE', 'AGGRESSIVE')",
            name="ck_portfolio_request_risk_preference",
        ),
        CheckConstraint(
            "return_preference IN ('DIVIDEND', 'CAPITAL_GAIN')",
            name="ck_portfolio_request_return_preference",
        ),
        CheckConstraint(
            "valuation_preference IN ('CURRENT_ASSET', 'FUTURE_EARNINGS')",
            name="ck_portfolio_request_valuation_preference",
        ),
    )

