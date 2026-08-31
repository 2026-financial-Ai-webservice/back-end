import asyncio

from sqlalchemy import text

from app.core.database import AsyncSessionLocal
from app.domain.screening.service import screen_companies


async def main():
    async with AsyncSessionLocal() as session:
        await screen_companies(session)
        total = (
            await session.execute(
                text("SELECT COUNT(*) FROM fundamental_screening")
            )
        ).scalar()
        passed = (
            await session.execute(
                text("SELECT COUNT(*) FROM fundamental_screening WHERE passed = true")
            )
        ).scalar()
        print(f"스크리닝 완료: 전체 {total}개 중 {passed}개 통과")

if __name__ == "__main__":
    asyncio.run(main())