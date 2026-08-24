from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, String, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MarketData(Base):
    __tablename__ = "market_data"

    corp_code: Mapped[str] = mapped_column(
        String(8), ForeignKey("companies.corp_code"), primary_key=True
    )
    market_date: Mapped[date] = mapped_column(Date, primary_key=True)
    current_price: Mapped[int | None] = mapped_column(BigInteger)
    listed_shares: Mapped[int | None] = mapped_column(BigInteger)
    market_cap: Mapped[int | None] = mapped_column(BigInteger)
    per: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    pbr: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    eps: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    bps: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
