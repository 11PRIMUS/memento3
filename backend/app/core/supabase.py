from supabase import create_client, Client
from app.core.config import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class SupabaseClient:
    _instance: Optional[Client] =None

    @classmethod
    def get_client(cls)->Client:
        if cls._instance is None:
            if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                raise ValueError("supabase config missing")
            
            try:
                cls._instance = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_KEY
            )
                logger.info("supabase client initialized")
            except Exception as e:
                logger.error(f"supabase connection failed: {e}")
                raise
        return cls._instance
    
    @classmethod
    def test_connection(cls) -> bool:
        try:
            client = cls.get_client()
            response = client.table('repositories').select('id').limit(1).execute()
            return True
        
        except Exception:
            return False
    
def get_supabase() -> Client:
    return SupabaseClient.get_client()
    
        