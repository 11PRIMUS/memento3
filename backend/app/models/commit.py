from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class Commit(BaseModel):
    id:Optional[int] =None
    repository_id:int =Field(..., gt=0)
    sha: str =Field(..., min_length=40, max_length=40)
    message:str = Field(..., min_length=1)
    author:str
    author_email: Optional[str] = None
    commit_date: datetime
    
    #commit stats
    additions: int = 0
    deletions: int = 0
    files_changed: List[str] = []
    
    #emedding metadata
    embedding_id: Optional[str] = None
    embedding_created_at: Optional[datetime] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class CommitDiff(BaseModel):
    id: Optional[int] = None
    commit_id: int = Field(..., gt=0)
    file_path: str = Field(..., min_length=1)
    diff_content: str
    additions: int = 0
    deletions: int = 0
    created_at: Optional[datetime] = None