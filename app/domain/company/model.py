from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Company(Base):
    __tablename__ = "companies"

    corp_code: Mapped[str] = mapped_column(
        String(8),
        primary_key=True
    )

    stock_code: Mapped[str|None] = mapped_column(
        String(6),
        unique=True,
        nullable=True
    )

    corp_name: Mapped[str]=mapped_column(
        String(100),
        nullable=False
    )

    industry_category:Mapped[str|None]=mapped_column(
        String(255),
        nullable=True
    )

    industry_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    is_manufacturing: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("now()"),
    )

