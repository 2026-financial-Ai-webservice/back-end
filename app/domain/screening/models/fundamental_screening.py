import datetime
from sqlalchemy import String, Integer, BigInteger, Text, Boolean, ForeignKey, UniqueConstraint, func, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class FundamentalScreening(Base):
    __tablename__ = "fundamental_screening"

    financial_screening_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    corp_code: Mapped[str] = mapped_column(String(8), ForeignKey("companies.corp_code"), nullable=False)
    business_year: Mapped[int] = mapped_column(Integer, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    fail_reasons: Mapped[str | None] = mapped_column(Text, nullable=True)
    screened_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # 최신 상태만 반영 (이력 저장 x)
    __table_args__ = (
        UniqueConstraint("corp_code", name="uq_fundamental_screening_corp_code"),
    )