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
    description: Optional[str]
    default_branch: str
    
    # GitHub metadata
    github_id: Optional[int]
    stars: int
    forks: int
    language: Optional[str]
    
    # Analysis metadata
    status: str
    total_commits: int
    indexed_commits: int
    last_analyzed_at: Optional[datetime]
    
    created_at: datetime
    updated_at: datetime

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