import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import random
# Connection details come from configuration, never hardcoded: these are
# one-off maintenance scripts and they live in a public repository.
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.core.config import settings

async def main():
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client.get_database("turnpike_analyst")
    
    count = await db.blogs.count_documents({})
    print(f"Total blog posts: {count}")
    
    if count < 27:
        needed = 27 - count
        print(f"Inserting {needed} more blog posts...")
        posts = []
        for i in range(needed):
            posts.append({
                "title": f"Blog Post {count + i + 1}",
                "slug": f"blog-post-{count + i + 1}",
                "summary": f"Summary for blog post {count + i + 1}.",
                "content": f"Content for blog post {count + i + 1}. This is just placeholder content to test pagination.",
                "author": "Test Author",
                "category": "INSIGHTS",
                "is_published": True,
                "published_at": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            })
        await db.blogs.insert_many(posts)
        print("Inserted!")
        
    count_after = await db.blogs.count_documents({})
    print(f"Total blog posts after: {count_after}")

if __name__ == "__main__":
    asyncio.run(main())
