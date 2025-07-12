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
from datetime import datetime, timezone

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
    
    async def index_repoCommmits(self, repo_id: int)->bool:
        try:
            logger.info("starting repository embedding indexing", repo_id=repo_id)
            #all commits
            commits = await self.supabase_service.get_commits(repo_id, limit=1000)
            
            if not commits:
                logger.warning("No commits found for repository", repo_id=repo_id)
                return False
            commits_to_embed = [] #filter without embeddings
            for commit in commits:
                if not commit.embedding_id:
                    commits_to_embed.append(commit)
            
            if not commits_to_embed:
                logger.info("all commits already have embeddings", repo_id=repo_id)
                return True
            
            logger.info("Commits to embed", repo_id=repo_id, count=len(commits_to_embed))
            
            batch_size = 50
            total_embedded = 0
            
            for i in range(0, len(commits_to_embed), batch_size):
                batch = commits_to_embed[i:i + batch_size]
                
                try:
                    embeddings = await self.embed_commitBatch(batch)
                    for embedding in embeddings:
                        await self.supabase_service.store_embedding(embedding)
                    
                    total_embedded += len(embeddings)
                    
                    logger.info("Batch processed", repo_id=repo_id, 
                              batch=i//batch_size + 1, embedded=len(embeddings))
                    
                except Exception as e:
                    logger.error("error processing batch", repo_id=repo_id, 
                               batch=i//batch_size + 1, error=str(e))
                    continue
            
            logger.info("embedding indexing completed", 
                       repo_id=repo_id, total_embedded=total_embedded)
            return True
            
        except Exception as e:
            logger.error("error indexing repository commits", repo_id=repo_id, error=str(e))
            return False
    
    async def similar_commits(self,query: str, repo_id: int, 
                                   limit: int = 10, threshold: float = 0.7) -> List[EmbeddingResult]:
        try:
            logger.info("searching similar commits", repo_id=repo_id, query_length=len(query))
            
            query_embeddings =await self.create_embeddings([query])
            query_embedding = query_embeddings[0].tolist()
            
            similar_commits = await self.supabase_service.search_similar_commits(
                query_embedding, repo_id, limit, threshold
            )
            
            # Convert to EmbeddingResult objects
            results = []
            for commit_data in similar_commits:
                result = EmbeddingResult(
                    commit_id=commit_data["commit_id"],
                    sha=commit_data["sha"],
                    message=commit_data["message"],
                    author=commit_data["author"],
                    commit_date=datetime.fromisoformat(commit_data["commit_date"]),
                    similarity_score=commit_data["similarity"],
                    files_changed=commit_data["files_changed"] or []
                )
                results.append(result)
            
            logger.info("similar commits found", repo_id=repo_id, count=len(results))
            return results
        except Exception as e:
            logger.error("Error searching similar commits", repo_id=repo_id, error=str(e))
            return []
    
    async def get_embedding_stats(self, repo_id: int) -> Dict[str, Any]:
        try:
            stats = await self.supabase_service.get_repository_stats(repo_id)
            
            return {
                "total_commits": stats.get("total_commits", 0),
                "embedded_commits": stats.get("total_embeddings", 0),
                "embedding_progress": stats.get("embedding_progress", 0.0),
                "model_name": self.model_name,
                "embedding_dimension": settings.EMBEDDING_DIMENSION
            }
            
        except Exception as e:
            logger.error("Error getting embedding stats", repo_id=repo_id, error=str(e))
            return {}
        
    async def delete_repository_embeddings(self, repo_id: int) -> bool:
        try:
            logger.info("Deleting repository embeddings", repo_id=repo_id)
            
            commits =await self.supabase_service.get_commits(repo_id)
            
            if not commits:
                logger.info("no commits found for repository", repo_id=repo_id)
                return True
            
            deleted_count = 0
            for commit in commits:
                if commit.embedding_id:
                    success =await self.supabase_service.delete_embedding(commit.id)
                    if success:
                        deleted_count +=1
            
            logger.info("repository embeddings deleted", repo_id=repo_id, 
                       deleted=deleted_count)
            return True
            
        except Exception as e:
            logger.error("error deleting repository embeddings", repo_id=repo_id, error=str(e))
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "dimension": settings.EMBEDDING_DIMENSION,
            "is_loaded": self.model is not None,
            "model_type": "sentence-transformers"
        }
