from app.core.logging import get_logger
from app.core.supabase import get_supabase
from app.models.repo import Repo, RepoStatus
from app.models.commit import Commit, CommitDiff
from app.models.embedding import Embeddings
from supabase import Client
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

logger = get_logger(__name__)

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
            response =self.client.table('repositories').insert(insert_data).execute()

            if response.data:
                logger.info("repository created", repo_id = response.data[0]['id'])
                return Repo(**response.data[0])
            else:
                raise Exception("failed to create repository")
            
        except Exception as e:
            logger.error("error creating repository", error=str(e))
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
    
    async def list_repo(self):
        try:
            response=self.client.table("repositories").select("*").execute()
            return response.data
        except Exception as e:
            raise Exception(f"error fetching repositories: {str(e)}")
        
    async def store_commits(self, repo_id: int, commits: List[Commit]) -> List[Commit]:
        #store commit in batch
        try:
            commit_data = []
            for commit in commits:
                commit_data.append({
                    "repository_id": repo_id,
                    "sha": commit.sha,
                    "message": commit.message,
                    "author": commit.author,
                    "author_email": commit.author_email,
                    "commit_date": commit.commit_date.isoformat(),
                    "additions": commit.additions,
                    "deletions": commit.deletions,
                    "files_changed": commit.files_changed,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
        
            stored_commits = []
            batch_size = 100
            
            for i in range(0, len(commit_data), batch_size):
                batch = commit_data[i:i + batch_size]
                try:
                    response = self.client.table('commits').insert(batch).execute()
                
                    if response.data:
                        for commit_item in response.data:
                            if isinstance(commit_item.get('commit_date'),str):
                                commit_item['commit_date']=datetime.fromisoformat(
                                    commit_item['commit_date'].replace('Z','+00:00')
                                )
                            stored_commits.append(Commit(**commit_item))
                        logger.debug("Stored commit batch", batch_num=i//batch_size + 1, count=len(response.data))
                
                except Exception as batch_error:
                    if "duplicate" in str(batch_error).lower() or "unique" in str(batch_error).lower():
                        logger.debug("skipping duplicate commits")
                        continue
                    else:
                        raise batch_error
                

            logger.info("Commits stored successfully", repo_id=repo_id, total=len(stored_commits))
            return stored_commits
            
        except Exception as e:
            logger.error("Error storing commits", repo_id=repo_id, error=str(e))
            raise

    async def get_commits(self, repo_id: int, limit: int = 100, offset: int = 0) -> List[Commit]:
        #get commit with pagination
        try:
            response = (
                self.client.table('commits')
                .select('*')
                .eq('repository_id', repo_id)
                .order('commit_date', desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            commits=[]
            for commit_data in response.data:
                if isinstance(commit_data.get('commit_date'),str):
                    commit_data['commit_date']=datetime.fromisoformat(commit_data['commit_date'].replace('Z','+00:00'))
                commits.append(Commit(**commit_data))

            return commits
            
        except Exception as e:
            logger.error("Error fetching commits", repo_id=repo_id, error=str(e))
            return []
        
    async def get_commit_by_sha(self, repo_id: int, sha: str) -> Optional[Commit]:
        #get commit by sha
        try:
            response = (
                self.client.table('commits')
                .select('*')
                .eq('repository_id', repo_id)
                .eq('sha', sha)
                .execute()
            )
            
            if response.data:
                return Commit(**response.data[0])
            return None
            
        except Exception as e:
            logger.error("error fetching commit by SHA", repo_id=repo_id, sha=sha[:8], error=str(e))
            return None
        
    async def store_embedding(self, embedding: Embeddings) -> Embeddings:
        #store embeddings
        try:
            embedding_data = {
                "commit_id": embedding.commit_id,
                "embedding_vector": embedding.embedding_vector,
                "model_name": embedding.model_name,
                "text_content": embedding.text_content,
                "embedding_type": embedding.embedding_type,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            response = self.client.table('embeddings').insert(embedding_data).execute()
            
            if response.data:
                logger.debug("embedding stored", commit_id=embedding.commit_id)
                return Embeddings(**response.data[0])
            else:
                raise Exception("failed to store embedding")
                
        except Exception as e:
            logger.error("Error storing embedding", commit_id=embedding.commit_id, error=str(e))
            raise

    async def search_similarCommits(self, query_embedding: List[float], repo_id: int, 
                                   limit: int = 10, threshold: float = 0.7) -> List[Dict]:
        #search for similar commits using vector 
        try:
            #supabase vector search function
            response = self.client.rpc('search_similar_commits', {
                'query_embedding': query_embedding,
                'repo_id': repo_id,
                'match_threshold': threshold,
                'match_count': limit
            }).execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error("Error searching similar commits", repo_id=repo_id, error=str(e))
            return []
        
    async def get_repository_stats(self, repo_id: int) -> Dict[str, Any]:
        #get repository statistics
        try:
            #commit count
            commits_response = (
                self.client.table('commits')
                .select('id', count='exact')
                .eq('repository_id', repo_id)
                .execute()
            )
            
            # embedding count
            embeddings_response = (
                self.client.table('embeddings')
                .select('id', count='exact')
                .eq('commit_id', 'in', f"(SELECT id FROM commits WHERE repository_id = {repo_id})")
                .execute()
            )
            
            total_commits = commits_response.count or 0
            total_embeddings = embeddings_response.count or 0
            
            return {
                "total_commits": total_commits,
                "total_embeddings": total_embeddings,
                "embedding_progress": total_embeddings / total_commits if total_commits > 0 else 0.0,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error("error getting repository stats", repo_id=repo_id, error=str(e))
            return {} 
    
    async def get_global(self)-> Dict[str, Any]:
        try:
            repos_response=self.client.table('repositories').select('id', count='exact').execute()
            commits_response=self.client.table('commits').select('id', count='exact').execute()
            embeddings_response=self.client.table('embeddings').select('id',count='exact').execute()

            return{
                "total_repositories": repos_response.count or 0,
                "total_commits": commits_response.count or 0,
                "total_embeddings":embeddings_response.count or 0,
                "last_updated":datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error("Error getting global stats", error=str(e))
            return {}
            
    


