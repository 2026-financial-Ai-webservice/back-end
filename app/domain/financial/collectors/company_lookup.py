from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.company.model import Company


async def get_corp_codes(session: AsyncSession) -> set[str]:
    """DART corp_code 중 companies 테이블에 등록된 것만"""
    rows = (await session.execute(select(Company.corp_code))).scalars().all()
    return set(rows)
