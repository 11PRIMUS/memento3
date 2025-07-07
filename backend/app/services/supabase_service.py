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

    async def get_repoURL(self, url:str)->Optional[Repo]:
        # get repo by url
        try:
            response = self.client.table('repositories').select('*').eq('url',str(url)).execute()

            if response.data:
                return Repo(**response.data[0])
            
            return None
        except Exception as e:
            logger.error("error fetching repostiory by url" ,error=str(e))
            return None
        
    async def get_repo(self, repo_id:int)-> Optional[Repo]:
        # get repository bu id
        try:
            response = self.client.table('repositories').select('*').eq('id', repo_id).execute()
            
            if response.data:
                return Repo(**response.data[0])
            return None
            
        except Exception as e:
            logger.error("Error fetching repository", repo_id=repo_id, error=str(e))
            return None
        
    async def update_repoStatus(self, repo_id:int, status: RepoStatus, **kwargs)-> bool:
        try:
            update_data = {
                "status": status.value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                **kwargs
            }
            
            response = self.client.table('repositories').update(update_data).eq('id', repo_id).execute()
            
            if response.data:
                logger.info("repository status updated", repo_id=repo_id, status=status.value)
                return True
            return False
            
        except Exception as e:
            logger.error("error updating repository", repo_id=repo_id, error=str(e))
            return False
        
    
    


