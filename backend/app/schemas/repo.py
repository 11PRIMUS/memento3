from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List
from datetime import datetime
from app.models.repo import RepoStatus

class RepoCreate(BaseModel):
    url: HttpUrl = Field(..., description="GitHub repository URL")
    max_commits: Optional[int] = Field(100, ge=1, le=1000, description="Maximum commits to fetch")

class RepoResponse(BaseModel):
    id: int
    name: str
    url: str
    owner: str
    description: Optional[str]= None
    default_branch: Optional[str]="main"
    
    # GitHub metadata
    github_id: Optional[int]=None
    stars: int
    forks: int
    language: Optional[str]= None
    
    # Analysis metadata
    status: str
    total_commits: int
    indexed_commits: int
    last_analyzed_at: Optional[datetime]=None
    
    created_at: datetime
    updated_at: datetime

class Config:
    from_attributes=True

@classmethod
def from_repository(cls, repo):
    return cls(
        id=repo.id,
        name=repo.name,
        url=repo.url,
        owner=repo.owner,
        description=repo.description,
        default_branch=repo.default_branch or "main",  # Provide default
        github_id=repo.github_id,                      # Can be None
        stars=repo.stars or 0,
        forks=repo.forks or 0,
        language=repo.language,
        status=repo.status,
        total_commits=repo.total_commits or 0,
        indexed_commits=repo.indexed_commits or 0,
        last_analyzed_at=repo.last_analyzed_at,
        created_at=repo.created_at,
        updated_at=repo.updated_at   

    )

class RepoList(BaseModel):
    repositories: List[RepoResponse]
    total: int
    page: int
    per_page: int
    has_next: bool

class RepoStats(BaseModel):
    repository_id: int
    total_commits: int
    recent_commits: int
    embedding_progress: float  # 0.0 to 1.0
    last_updated: datetime