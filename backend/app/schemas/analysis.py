from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class AnalysisRequest(BaseModel):
    repository_id: int =Field(..., gt=0)
    questions: str =Field(..., min_length=1, max_length=1000)
    max_commits: Optional[int] =Field(10, ge=1, le=50)
    similarity_t: Optional[float] =Field(0.7, ge=0.0, le=1.0)

class Commit_refrence(BaseModel):
    sha: str
    message: str
    author: str
    commit_date: str
    files_changes: str
    additions: str
    deletions: str

class AnalysisResponse(BaseModel):
    question: str
    answer: str
    relevant_commits: List[Commit_refrence]
    confidence_score: float
    processing_time: float
    repository_id: int

class AnalysisHistory(BaseModel):
    id: int
    question: str
    answer: str
    confidence_score: float
    processing_time: float
    created_at: datetime
    relevant_commit_count: int

class AnalysisHistoryList(BaseModel):
    analyses: List[AnalysisHistory]
    total: str
    page: str
    per_page: int
    has_next: float
