from app.core.logging import logging
from app.models.repo import Repo, RepoStatus
from app.models.commit import Commit, CommitDiff
from app.models.embedding import Embeddings
from supabase import Client
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class SupabaseService:
    def __init__(self, client: Client):
        self.client =client

    #repository operations
    async def create_repo(self, repo_data: Dict[str, Any])-> Repo:
        """new repository record"""
        try:
            insert_data={
                **repo_data,
                "created_at":datetime.now(timezone.utc).isoformat(),
                "updated_at":datetime.now(timezone.utc).isoformat()
            }
            response =self.client.table('repostories').insert(insert_data).execute()

            if response.data:
                logger.info("repository created", repo_id = response.data[0]['id'])
                return Repo(**response.data[0])
            else:
                raise Exception("failed to create repository")
            
        except Exception as e:
            logger.erro("error creating repository", error=str(e))
            raise
    
    

