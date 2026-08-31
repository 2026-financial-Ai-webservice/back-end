import asyncio

from app.domain.marketdata.collectors.kis_client import KisMarketDataClient


async def main() -> None:
    async with KisMarketDataClient() as client:
        token = await client.issue_access_token()
    print(token)


if __name__ == "__main__":
    asyncio.run(main())
