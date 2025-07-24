from supabase import create_client, SupabaseClient
from app.core.config import settings
from typing import Optional
from app.core.logging import get_logger
from functools import lru_cache
import asyncio

logger = get_logger(__name__)

class SupabaseManager:
    _instance: Optional['SupabaseManager'] = None
    _client: Optional[SupabaseClient] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self.initialize_client()

    def initialize_client(self):
        try:
            if not settings.SUPABASE_URL:
                raise ValueError("Supabase URL is required")

            if not settings.SUPABASE_KEY:
                raise ValueError("Supabase key is required")

            self._client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY
            )

            logger.info("Supabase client initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize Supabase client", error=str(e))
            raise

    @classmethod
    def get_client(cls) -> SupabaseClient:
        instance = cls()
        if instance._client is None:
            raise Exception("Supabase client not initialized")
        return instance._client

    @classmethod
    def test_connection(cls) -> bool:
        try:
            client = cls.get_client()
            # v2.x uses `.execute()` to get the result
            response = client.table('repositories').select('id').limit(1).execute()
            logger.info("Supabase connection test successful")
            return True
        except Exception as e:
            logger.error("Supabase connection test failed", error=str(e))
            return False


@lru_cache()
def get_supabase() -> SupabaseClient:
    """FastAPI dependency to get Supabase client"""
    return SupabaseManager.get_client()


class SupabaseHealthCheck:
    """Health check utilities for Supabase"""

    @staticmethod
    async def check_database_connection() -> dict:
        """Check database connection health"""
        try:
            client = SupabaseManager.get_client()
            start_time = asyncio.get_event_loop().time()
            response = client.table('repositories').select('count').execute()
            end_time = asyncio.get_event_loop().time()

            response_time = (end_time - start_time) * 1000

            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "url": settings.SUPABASE_URL,
                "tables_accessible": True
            }
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "url": settings.SUPABASE_URL,
                "tables_accessible": False
            }

# The DATABASE_SCHEMA remains unchanged
DATABASE_SCHEMA = """ ... """

async def initialize_database():
    logger.info("db schema :")
    return DATABASE_SCHEMA
