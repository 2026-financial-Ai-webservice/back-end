import asyncio
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.domain.financial.collectors.company_lookup import get_corp_codes
from app.domain.financial.collectors.financial_statements import collect_financial_statements, YEARS
from app.domain.financial.collectors.ratio_calculator import calculate_ratios


async def main():
    async with AsyncSessionLocal() as session:
        corp_codes = await get_corp_codes(session)

        for dart_corp_code in corp_codes:
            try:
                await collect_financial_statements(session, settings.DART_API_KEY, dart_corp_code)
                for year in YEARS:
                    await calculate_ratios(session, dart_corp_code, year)
            except Exception as exc:
                print(f"[실패] {dart_corp_code}: {exc}")
                await session.rollback()
                continue

if __name__ == "__main__":
    asyncio.run(main())