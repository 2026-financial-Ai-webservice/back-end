import asyncio
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM companies"))
        print("companies 행 개수:", result.scalar())

        rows = await session.execute(text("SELECT corp_code, corp_name, stock_code FROM companies LIMIT 5"))
        for row in rows:
            print(row)

asyncio.run(main())
