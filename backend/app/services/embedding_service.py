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
    
    async def embed_commit_message(self, commit: Commit) -> Embeddings:
        #create embedding for commit message
        text_content = f"{commit.message} {' '.join(commit.files_changed[:5])}"
        
        embeddings = await self.create_embeddings([text_content])
        
        return Embeddings(
            commit_id=commit.id,
            embedding_vector=embeddings[0].tolist(),
            model_name=self.model_name,
            text_content=text_content,
            embedding_type="commit_message"
        )
    
    async def embed_commitBatch(self, commits: List[Commit]) -> List[Embeddings]:
        #create embeddings for multiple commits
        if not commits:
            return []
        
        logger.info("Creating embeddings for commit batch", count=len(commits))
        
        texts = []
        for commit in commits:
            text_content = f"{commit.message} {' '.join(commit.files_changed[:5])}"
            texts.append(text_content)
        
        embeddings_array = await self.create_embeddings(texts)
        
        #embedding objects
        embeddings = []
        for i, commit in enumerate(commits):
            embedding = Embeddings(
                commit_id=commit.id,
                embedding_vector=embeddings_array[i].tolist(),
                model_name=self.model_name,
                text_content=texts[i],
                embedding_type="commit_message"
            )
            embeddings.append(embedding)
        
        logger.info("embeddings created successfully", count=len(embeddings))
        return embeddings
    
    