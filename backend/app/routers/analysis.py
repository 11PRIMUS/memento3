from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client
from typing import Optional
from app.core.logging import get_logger
from app.core.supabase import get_supabase
from app.services.supabase_service import SupabaseService
from app.services.embedding_service import EmbeddingService




logger = get_logger(__name__)
router=APIRouter()

def get_supabaseSerive(client: Client= Depends(get_supabase))->SupabaseService:
    return SupabaseService (client)

def get_embeddingSerive(client: Client=Depends(get_supabase))->EmbeddingService:
    return EmbeddingService(client)
