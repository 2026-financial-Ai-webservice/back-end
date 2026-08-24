from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.company.model import Company
from app.domain.marketdata.model import MarketData


class ListedCompany(TypedDict):
    corp_code: str
    stock_code: str


class MarketDataValues(TypedDict):
    corp_code: str
    market_date: date
    current_price: int | None
    listed_shares: int | None
    market_cap: int | None
    per: Decimal | None
    pbr: Decimal | None
    eps: Decimal | None
    bps: Decimal | None


async def get_listed_companies(session: AsyncSession) -> list[ListedCompany]:
    result = await session.execute(
        select(Company.corp_code, Company.stock_code)
        .where(Company.stock_code.is_not(None))
        .order_by(Company.corp_code)
    )
    return [
        {"corp_code": corp_code, "stock_code": stock_code}
        for corp_code, stock_code in result.all()
        if stock_code is not None
    ]


async def upsert_market_data(
    session: AsyncSession, values: list[MarketDataValues]
) -> None:
    if not values:
        return
    statement = pg_insert(MarketData).values(values)
    statement = statement.on_conflict_do_update(
        index_elements=[MarketData.corp_code, MarketData.market_date],
        set_={
            "current_price": statement.excluded.current_price,
            "listed_shares": statement.excluded.listed_shares,
            "market_cap": statement.excluded.market_cap,
            "per": statement.excluded.per,
            "pbr": statement.excluded.pbr,
            "eps": statement.excluded.eps,
            "bps": statement.excluded.bps,
        },
    )
    await session.execute(statement)
