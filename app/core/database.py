import logging
import redis.asyncio as redis
from psycopg_pool import AsyncConnectionPool
from app.core.config import settings

logger = logging.getLogger("uvicorn")

class Database:
    def __init__(self):
        self.pg_pool = None
        self.redis = None

    async def connect(self):
        # 1. Postgres Connection
        try:
            self.pg_pool = AsyncConnectionPool(
                conninfo=settings.DATABASE_URL, 
                max_size=20, 
                kwargs={"autocommit": True},
                open=False
            )
            await self.pg_pool.open()
            logger.info("✅ Postgres (Async) connected.")
        except Exception as e:
            logger.error(f"❌ Postgres connection failed: {e}")
            raise e

        # 2. Redis Connection
        try:
            self.redis = redis.from_url(
                settings.REDIS_URL, 
                encoding="utf-8", 
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("✅ Redis connected.")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise e

    async def close(self):
        if self.pg_pool:
            await self.pg_pool.close()
            logger.info("🔻 Postgres closed.")
        if self.redis:
            await self.redis.close()
            logger.info("🔻 Redis closed.")

    def get_pg_pool(self):
        if not self.pg_pool:
            raise Exception("Postgres not connected")
        return self.pg_pool

    def get_redis(self):
        if not self.redis:
            raise Exception("Redis not connected")
        return self.redis

# Singleton Instance
db = Database()