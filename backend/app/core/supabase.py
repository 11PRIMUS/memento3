from supabase import create_client, Client
from app.core.config import settings
from typing import Optional

class SupabaseClient:
    _instance: Optional[Client] =None

    @classmethod
    def get_client(cls)->Client:
        if cls._instance is None:
            if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                raise ValueError("supabase config missing")
            
            cls._instance = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY
            )
        return cls._instance
    
def get_supabase() -> Client:
    return SupabaseClient.get_client()
    
        