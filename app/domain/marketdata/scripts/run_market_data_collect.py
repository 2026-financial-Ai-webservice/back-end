import asyncio
import logging

from app.core.database import AsyncSessionLocal
from app.domain.marketdata.service import collect_market_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)


async def main() -> None:
    async with AsyncSessionLocal() as session:
        count = await collect_market_data(session)

    print(f"시장 데이터 {count}건 저장 완료")


if __name__ == "__main__":
    asyncio.run(main())