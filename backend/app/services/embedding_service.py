from app.core.config import settings
from app.core.logging import get_logger
from app.models.embedding import Embeddings, EmbeddingResult
from app.models.commit import Commit
from app.services.supabase_service import SupabaseService
from sentence_transformers import SentenceTransformer
from supabase import Client
from typing import Optional, List, Dict, Any
import numpy as np
import asyncio

logger=get_logger(__name__)

class EmbeddingService:
    def __init__(self, supabase_client: Client):
    
        self.supabase_service = SupabaseService(supabase_client)
        self.model = None 
        self.model_name = settings.EMBEDDING_MODEL
    
    def _load_model(self):
        #lazy load the embedding model
        if self.model is None:
            logger.info("Loading embedding model", model=self.model_name)
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully")
    
    async def create_embeddings(self, texts: List[str]) -> np.ndarray:
        #generate embeddings for texts"""
        if not texts:
            return np.array([])
        
        self._load_model()
        
        #thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None, self.model.encode, texts
        )
        
        logger.debug("Generated embeddings", count=len(texts), dimension=embeddings.shape[1])
        return embeddings