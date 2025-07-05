from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum

class RepoStatus(str, Enum):
    PENDING= "pending"
    INDEXING= "indexing"
    COMPLETED= "completed"
    ERROR= "error"

class Repo(BaseModel):
    """repo model"""
    id:Optional[int] =None
    name: str= Field(..., min_length=1, max_length=250)
    description: Optional[str] = None
    url: str =Field(..., min_length=1)
    language: Optional[str] =None

    owner:Optional[str] =None
    stars: int=0
    forks: int=0
    status: RepoStatus = RepoStatus.PENDING
    total_commits: int=0
    indexed_commits: int=0
    last_analyzed_at: Optional[datetime] =None

    #timestamp
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        if not v.startswith(('https://', 'http://', 'git@')):
            raise ValueError('invalid repo url')
        
        return v
    
    class Config:
        use_enum_values =True
        json_encoders={
            datetime: lambda v:v.isoformat() if v else None
        }
