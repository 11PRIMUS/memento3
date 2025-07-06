from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class CommitResponse(BaseModel):
    id: str
    sha: str
    message: str
    author: str
    author_email: Optional[str]
    commit_date: datetime
    additions: str
    deletions: str
    files_changed: str
    has_embedding: bool

class CommitList(BaseModel):
    commits: List[CommitResponse]
    total: int
    page: int
    per_page: int
    has_next: bool

class CommitDetail(CommitResponse):
    diff_content: Optional[str] =None
    embedding_created_at: Optional[datetime] =None