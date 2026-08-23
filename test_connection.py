import asyncio
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM financial_statements"))
        print("financial_statements 행 개수:", result.scalar())

        rows = await session.execute(text("SELECT * FROM financial_statements LIMIT 5"))
        for row in rows:
            print(row)

asyncio.run(main())
