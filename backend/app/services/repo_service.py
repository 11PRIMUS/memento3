from supabase import Client
from typing import List, Optional
from datetime import datetime, timezone
from app.models.repo import Repo

class RepoServices():
    """service for repo operations"""

    def __init__(self, supabase:Client):
        self.supabase =supabase
        self.table ="repositories"
    
    async def create_repo(self, repo: Repo)-> Repo:
        repo_data = repo.model_dump(exclude={'id'})
        repo_data['created_at'] = datetime.now(timezone.utc).isoformat()
        repo_data['updated_at'] = datetime.now(timezone.utc).isoformat()

        response = self.supabase.table(self.table).insert(repo_data).execute()
        if response.data:
            return Repo(**response.data[0])
        else:
            raise Exception("failed to create new repo")
        
    async def get_repo(self, repo_id:int)->Optional[Repo]:
        """get repo by id"""
        response = self.supabase.table(self.table).select('*').eq('id', repo_id).execute()
        
        if response.data:
            return Repo(**response.data[0])
        return None
    
    async def get_repos(self, limit: int = 50) -> List[Repo]:
        """get list of repositories"""
        response = (
            self.supabase.table(self.table)
            .select('*')
            .order('created_at', desc=True)
            .limit(limit)
            .execute()
        )
        
        return [Repo(**repo) for repo in response.data]
    
    async def repo_exists(self, url: str) -> bool:
        """Check if repo exist """
        response = self.supabase.table(self.table).select('id').eq('url', url).execute()
        return len(response.data) > 0