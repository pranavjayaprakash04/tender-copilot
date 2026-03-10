import asyncio
from sqlalchemy import text
from app.database import engine

async def test():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        print('Database connected successfully:', result.fetchone())

if __name__ == "__main__":
    asyncio.run(test())
