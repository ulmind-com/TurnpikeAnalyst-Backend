import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def main():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['turnpike']
    docs = await db.blogs.find().to_list(100)
    print(len(docs))
    print([d['title'] for d in docs])

asyncio.run(main())
