import asyncio

from app.core.database import AsyncSessionLocal
from app.domain.financial.collectors.company_lookup import get_corp_codes
from app.domain.financial.collectors.financial_statements import YEARS
from app.domain.financial.collectors.ratio_calculator import calculate_ratios


async def main():
    async with AsyncSessionLocal() as session:
        corp_codes = await get_corp_codes(session)
        total = len(corp_codes)
        failed = []

        for i, corp_code in enumerate(corp_codes, start=1):
            for year in YEARS:
                try:
                    await calculate_ratios(session, corp_code, year)
                except Exception as exc:
                    print(f"[실패] {corp_code} {year}: {exc}")
                    await session.rollback()
                    failed.append((corp_code, year))
            if i % 100 == 0 or i == total:
                print(f"[진행] {i}/{total}")

        print(f"완료. 실패 {len(failed)}건: {failed}")

if __name__ == "__main__":
    asyncio.run(main())
