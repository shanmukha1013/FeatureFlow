import asyncio
from app.storage.database import engine
from app.storage.models import Base

async def reset():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        print("Dropped and recreated tables!")

if __name__ == "__main__":
    asyncio.run(reset())
