from sqlalchemy import String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Company(Base):
    __tablename__ = "companies"

    corp_code: Mapped[str] = mapped_column(String(8), primary_key=True)
    corp_name: Mapped[str] = mapped_column(String(100), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(6), unique=True, nullable=True)