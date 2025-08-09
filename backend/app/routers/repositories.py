from app.core.supabase import get_supabase
from supabase import Client
from app.core.logging import get_logger
from app.services.supabase_service import SupabaseService
from app.services.github_service import Github_service
from app.services.embedding_service import EmbeddingService, EmbeddingResult, Embeddings
from app.schemas.repo import (
    RepoCreate, RepoResponse, RepoList, RepoStats
)
from app.schemas.commit import CommitResponse, CommitList
from app.models.repo import RepoStatus, Repo
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import Optional, List
from datetime import datetime,timezone
import asyncio

logger = get_logger(__name__)
router = APIRouter()

def get_supabaseService(client:Client =Depends(get_supabase))->SupabaseService:
    return SupabaseService(client)

def get_githubService()->Github_service:
    return Github_service()

def get_embeddingService(client: Client=Depends(get_supabase))->EmbeddingService:
    return EmbeddingService(client)

@router.post("/", response_model=RepoResponse)
async def create_repository(
    repo_data: RepoCreate,
    background_tasks: BackgroundTasks,
    supabase_service: SupabaseService = Depends(get_supabaseService),
    github_service: Github_service = Depends(get_githubService)


):
    try:
        logger.info("creating repository", url=str(repo_data.url))

        if not is_valid_github_url(str(repo_data.url)):
            raise HTTPException(status_code=400, detail="invalid github repo url format")

        existing_repo = await supabase_service.get_repoURL(str(repo_data.url))
        if existing_repo:
            logger.warning("Repository already exists", url=str(repo_data.url))
            return RepoResponse(**existing_repo.model_dump())
        
        #get repo info from github
        try:
            repo_info = await github_service.get_repoInfo(str(repo_data.url))
        except ValueError as e:
            logger.error("Invalid repository URL", url=str(repo_data.url), error=str(e))
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error("failed to fetch repo",url=str(repo_data.url),error=str(e))
            raise HTTPException (status_code=500, detail=f"failed to fetch repo info:{str(e)}")
        
        repo_record = await supabase_service.create_repo({
            "name": repo_info["name"],
            "url": str(repo_data.url),
            "owner": repo_info["owner"],
            "description": repo_info["description"],
            "default_branch": repo_info["default_branch"],
            "github_id": repo_info["github_id"],
            "stars": repo_info["stars"],
            "forks": repo_info["forks"],
            "language": repo_info["language"],
            "status": RepoStatus.PENDING.value
        })
        logger.info("repositor record created",repo_id=repo_record.id)
        background_tasks.add_task(
            process_repoCommits,
            repo_record.id,
            str(repo_data.url),
            repo_data.max_commits or 100
        )
        
        logger.info("Repository created successfully", repo_id=repo_record.id)
        return RepoResponse(**repo_record.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating repository", error=str(e))
        raise HTTPException(status_code=500, detail="internal server error")
    
def is_valid_github_url(url:str)-> bool:
    import re
    github_pattern=r'^https://github\.com/[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+/?$'
    return bool(re.match(github_pattern, url.rstrip('/')))


@router.get("/", response_model=RepoList)
async def list_repositories(
    page: int =Query(1, ge=1, description="Page number"),
    per_page:int = Query(20, ge=1, le=100, description="Items per page"),
    service:SupabaseService = Depends(get_supabaseService)
):
    try:
        offset =(page-1) * per_page
        all_repositories=await service.list_repo()
        total =len(all_repositories)
        start_idx= offset
        end_idx =offset + per_page
        repositories= all_repositories[start_idx:end_idx]
        
        has_next = end_idx < total
        
        logger.info("listed repositories",page=page, count=len(repositories))

        
        has_next = len(repositories) > per_page
        if has_next:
            repositories = repositories[:-1] 
        
        total=offset + len(repositories) + (1 if has_next else 0)
        
        logger.info("Listed repositories", page=page, count=len(repositories))
        
        repo_responses = []
        for repo in repositories:

            repo_dict=repo.model_dump() if hasattr(repo, 'model_dump') else repo.__dict__
            repo_dict.setdefault('default_branch', 'main')
            repo_dict.setdefault('github_id', None)
            repo_dict.setdefault('stars', 0)
            repo_dict.setdefault('forks', 0)
            repo_dict.setdefault('total_commits', 0)
            repo_dict.setdefault('indexed_commits', 0)
            
            repo_responses.append(RepoResponse(**repo_dict))
        
        return RepoList(
            repositories=repo_responses,
            total=total,
            page=page,
            per_page=per_page,
            has_next=has_next
        )
    except Exception as e:
        logger.error("error listing repo", error=str(e))
        raise HTTPException(status_code=500, detail="internal server error")
    
@router.get("/{repo_id}",response_model=RepoResponse)
async def get_repo(
    repo_id: int,
    service: SupabaseService= Depends(get_supabaseService)

):
    #get repo by id
    try:
        repository=await service.get_repo(repo_id)
        if not repository:
            raise HTTPException(status_code=404, detail="repo not found")
        logger.info("repo retireived", repo_id=repo_id)
        return RepoResponse(**repository.model_dump())
    
    except Exception as e:
        logger.error("error fetching repo",repo_id=repo_id, error=str(e))
        raise HTTPException(status_code=500, detail="internal server error")

@router.get("/{repo_id}/stats", response_model=RepoStats)
async def get_repoStats(
    repo_id:int,
    service: SupabaseService=Depends(get_supabaseService),
    embedding_service: EmbeddingService=Depends(get_embeddingService)
):
    #get repo statistics
    try:
        repository=await service.get_repo(repo_id)
        if not repository:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        stats = await embedding_service.get_embedding_stats(repo_id)
        
        logger.info("repository stats retrieved", repo_id=repo_id)
        return RepoStats(
            repository_id=repo_id,
            total_commits=stats.get("total_commits", 0),
            recent_commits=0,  #  need separate query
            embedding_progress=stats.get("embedding_progress", 0.0),
            last_updated=datetime.now(timezone.utc)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching repository stats", repo_id=repo_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
        
@router.get("/{repo_id}/commits",response_model=CommitList)
async def get_commits(
    repo_id: int,
    page: int=Query(1, ge=1,description="page number"),
    per_page: int=Query(50, ge=1, le=100, description="items per page"),
    service:SupabaseService=Depends(get_supabaseService)

):
    #get commits of repo
    try:
        repository = await service.get_repo(repo_id)
        if not repository:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        offset = (page - 1) * per_page
        commits = await service.get_commits(repo_id, limit=per_page + 1, offset=offset)

        has_next = len(commits) > per_page
        if has_next:
            commits = commits[:-1]
        
        commit_responses = []
        for commit in commits:
            commit_responses.append(CommitResponse(
                id=commit.id,
                sha=commit.sha,
                message=commit.message,
                author=commit.author,
                author_email=commit.author_email,
                commit_date=commit.commit_date,
                additions=commit.additions,
                deletions=commit.deletions,
                files_changed=commit.files_changed,
                has_embedding=commit.embedding_id is not None
            ))
        total = offset + len(commits) + (1 if has_next else 0)
        
        logger.info("repository commits retrieved", repo_id=repo_id, count=len(commits))
        
        return CommitList(
            commits=commit_responses,
            total=total,
            page=page,
            per_page=per_page,
            has_next=has_next
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching repository commits", repo_id=repo_id, error=str(e))
        raise HTTPException(status_code=500, detail="internal server error")

@router.post("/{repo_id}/reindex")
async def reindex_repo(
    repo_id: int,
    background_tasks: BackgroundTasks,
    service: SupabaseService=Depends(get_supabaseService),
    embedding_service: EmbeddingService=Depends(get_embeddingService)

):
    try:
        repository= await service.get_repo(repo_id)
        if not repository:
            raise HTTPException(status_code=404, detail="repository not found")
        background_tasks.add_task(
            reindex_repoEmbedding,
            repo_id,
            embedding_service
        )
        logger.info("repository reindexing started",repo_id=repo_id)
        return {"message":"reindexing started","repo_id": repo_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("error starting reindex", repo_id=repo_id, error=str(e))
        raise HTTPException(status_code=500, detail="internal server error")
    
@router.post("/{repo_id}/debug-process")
async def debug_process_repository(
    repo_id: int,
    background_tasks: BackgroundTasks,
    service: SupabaseService = Depends(get_supabaseService)
):
    """Debug endpoint to manually trigger repository processing"""
    try:
        repository = await service.get_repo(repo_id)
        if not repository:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        logger.info("Manually triggering repository processing", repo_id=repo_id)
        
        # Add background task
        background_tasks.add_task(
            process_repoCommits,
            repo_id,
            repository.url,
            100  # max_commits
        )
        
        return {
            "message": "Processing started",
            "repo_id": repo_id,
            "url": repository.url,
            "current_status": repository.status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error starting debug processing", repo_id=repo_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start processing")

@router.delete("/{repo_id}")
async def delete_repo(
    repo_id:int,
    service: SupabaseService=Depends(get_supabaseService),
    embedding_service: EmbeddingService=Depends(get_embeddingService)
):
    try:
        repository = await service.get_repo(repo_id)
        if not repository:
            raise HTTPException(status_code=404, detail="repo not found")
        await embedding_service.delete_repoEmbeddings(repo_id)
        success = await service.delete_repo(repo_id)

        if success:
            logger.info("repository deleted successfully")
            return {"message":"repository deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="failed to delete repository")
        
    except Exception as e:
        logger.error("error deleting repository",repo_id=repo_id, error=str(e))
        raise HTTPException(status_code=500, detail="internal server error")
    
async def process_repoCommits(repo_id: int, repo_url: str, max_commits: int):
    """Background task to process repository commits"""
    try:
        # Import here to avoid circular imports in background tasks
        from app.core.config import settings
        from app.core.supabase import get_supabase
        
        # Create new service instances for background task
        supabase_client = get_supabase()
        supabase_service = SupabaseService(supabase_client)
        github_service = Github_service()

        logger.info("Starting repository processing", repo_id=repo_id, url=repo_url, max_commits=max_commits)
        
        # Update status to indexing
        await supabase_service.update_repoStatus(repo_id, RepoStatus.INDEXING)
        logger.info("Repository status updated to INDEXING", repo_id=repo_id)
        
        # Get commits from GitHub repo with retry logic
        commits = []
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries and not commits:
            try:
                logger.info(f"Fetching commits (attempt {retry_count + 1})", repo_id=repo_id, repo_url=repo_url)
                commits = await github_service.get_commits(repo_url, max_commits)

                if commits:
                    logger.info("Commits fetched successfully", repo_id=repo_id, commit_count=len(commits))
                    break
                else:
                    logger.warning("No commits returned from GitHub", repo_id=repo_id, attempt=retry_count + 1)
                    
            except Exception as e:
                retry_count += 1
                logger.error(f"Error fetching commits (attempt {retry_count})", 
                           repo_id=repo_id, error=str(e))
                if retry_count < max_retries:
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                else:
                    raise e

        if commits:
            # Store commits in database
            logger.info("Storing commits in database", repo_id=repo_id, commit_count=len(commits))
            stored_commits = await supabase_service.store_commits(repo_id, commits)
            
            # Update repository with commit count
            if stored_commits:
                await supabase_service.update_repoStatus(
                    repo_id,
                    RepoStatus.COMPLETED,
                    total_commits=len(stored_commits),
                    indexed_commits=len(stored_commits),
                    last_analyzed_at=datetime.now(timezone.utc).isoformat()
                )
                
                logger.info("Repository processing completed successfully", repo_id=repo_id, 
                           commit_count=len(stored_commits))
            else:
                await supabase_service.update_repoStatus(repo_id, RepoStatus.ERROR)
                logger.error("Failed to store commits in database", repo_id=repo_id)

        else:
            logger.warning("No commits found for repository", repo_id=repo_id)
            await supabase_service.update_repoStatus(
                repo_id, 
                RepoStatus.COMPLETED,
                total_commits=0,
                indexed_commits=0,
                last_analyzed_at=datetime.now(timezone.utc).isoformat()
            )

    except Exception as e:
        logger.error("Error processing repository", repo_id=repo_id, error=str(e), exc_info=True)
        try:
            # Try to update status to error, but don't fail if this also fails
            from app.core.supabase import get_supabase
            supabase_client = get_supabase()
            supabase_service = SupabaseService(supabase_client)
            await supabase_service.update_repoStatus(repo_id, RepoStatus.ERROR)
        except Exception as update_error:
            logger.error("Failed to update repository status to ERROR", 
                        repo_id=repo_id, error=str(update_error))

async def reindex_repoEmbedding(repo_id: int, embedding_service: EmbeddingService):
    try:
        logger.info("starting embedding reindex", repo_id=repo_id)
        #delete existing embeddings
        await embedding_service.delete_repository_embeddings(repo_id)
        success=await embedding_service.index_repoCommmits(repo_id)

        if success:
           logger.info("embedding reindex completed", repo_id=repo_id)
        else:
            logger.error("embedding reindex failed", repo_id=repo_id)
            
    except Exception as e:
        logger.error("error reindexing embeddings",repo_id=repo_id, error=str(e)) 