from app.core.supabase import get_supabase
from supabase import Client
from app.core.logging import get_logger
from app.services.supabase_service import SupabaseService
from app.services.github_service import Github_service
from app.services.embedding_service import EmbeddingService
from app.schemas.repo import (
    RepoCreate, RepoResponse, RepoList, RepoStats
)
from app.schemas.commit import CommitResponse, CommitList
from app.models.repo import RepoStatus
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import Optional, List
from datetime import datetime,timezone

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
    supabase_service: SupabaseService = Depends(get_supabaseService),
    github_service: Github_service = Depends(get_githubService)

):
    try:
        logger.info("creating repository", url=str(repo_data.url))

        existing_repo = await supabase_service.get_repository_by_url(str(repo_data.url))
        if existing_repo:
            logger.warning("Repository already exists", url=str(repo_data.url))
            raise HTTPException(
                status_code=400,
                detail="Repository already exists"
            )
        
        #get repo info from github
        try:
            repo_info = await github_service.get_repository_info(str(repo_data.url))
        except ValueError as e:
            logger.error("Invalid repository URL", url=str(repo_data.url), error=str(e))
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error("failed to fetch repo",url=str(repo_data.url),error=str(e))
            raise HTTPException (status_code=500, detail=f"failed to fetch repo info:{str(e)}")
        
        repo_record = await supabase_service.create_repository({
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
        background_tasks.add_task(
            process_repository_commits,
            repo_record.id,
            str(repo_data.url),
            repo_data.max_commits or 100,
            supabase_service,
            github_service
        )
        
        logger.info("Repository created successfully", repo_id=repo_record.id)
        return RepoResponse(**repo_record.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating repository", error=str(e))
        raise HTTPException(status_code=500, detail="intenal server error")
    
@router.get("/", response_model=RepoList)
async def list_repositories(
    page: int =Query(1, ge=1, description="Page number"),
    per_page:int = Query(20, ge=1, le=100, description="Items per page"),
    service:SupabaseService = Depends(get_supabaseService)
):
    try:
        offset =(page-1) * per_page
        repositories =await service.list_repositories(limit=per_page + 1, offset=offset)
        
        has_next = len(repositories) > per_page
        if has_next:
            repositories = repositories[:-1] 
        
        total=offset + len(repositories) + (1 if has_next else 0)
        
        logger.info("Listed repositories", page=page, count=len(repositories))
        
        return RepoList(
            repositories=[RepoResponse(**repo.dict()) for repo in repositories],
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
        logger.errp("error fetching repo",repo_id=repo_id, error=str(e))
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
            reindex_repo,
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