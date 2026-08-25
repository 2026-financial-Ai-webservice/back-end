import asyncio

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.domain.financial.collectors.company_lookup import get_corp_codes
from app.domain.financial.collectors.dividend import collect_dividend
from app.domain.financial.collectors.financial_statements import YEARS


async def main():
    async with AsyncSessionLocal() as session:
        corp_codes = await get_corp_codes(session)
        total = len(corp_codes)

        for i, corp_code in enumerate(corp_codes, start=1):
            for year in YEARS:
                try:
                    await collect_dividend(session, settings.DART_API_KEY, corp_code, year)
                except Exception as exc:
                    print(f"[실패] {corp_code} {year}: {exc}")
                    await session.rollback()
            if i % 100 == 0 or i == total:
                print(f"[진행] {i}/{total}")

if __name__ == "__main__":
    asyncio.run(main())
