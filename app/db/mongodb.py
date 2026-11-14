import logging
import re

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

logger = logging.getLogger("uvicorn.error")


def _redact(uri: str) -> str:
    """Strip credentials from a connection string before it is logged.

    Logs are routinely shipped to aggregators and read by people who should
    not hold the database password.
    """
    return re.sub(r"://[^:/@]+:[^@]+@", "://***:***@", uri)

class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

    @classmethod
    def connect_db(cls):
        logger.info("Connecting to MongoDB at %s...", _redact(settings.MONGODB_URL))
        cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
        cls.db = cls.client[settings.DATABASE_NAME]
        logger.info("Connected to MongoDB successfully.")

    @classmethod
    def close_db(cls):
        logger.info("Closing MongoDB connection...")
        if cls.client is not None:
            cls.client.close()
            logger.info("MongoDB connection closed.")

    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        if cls.db is None:
            cls.connect_db()
        return cls.db

db_client = Database()

def get_db() -> AsyncIOMotorDatabase:
    return db_client.get_database()
