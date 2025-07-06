from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class Embeddings(BaseModel):
    id: Optional[int] = None
    commit_id: int= Field(..., gt=0)
    embedding_vector: List[float] =Field(..., min_items=1)
    model_name: str =Field(..., min_length=1)

    text_content: str #embedded text
    embedding_type: str="commit_message"

    created_at: Optional[datetime] = None

    class Config:
        json_encoders={
            datetime: lambda v:v.isoformat() if v else None
        }

class EmbeddingSearch(BaseModel):
    query: str = Field(..., min_length=1)
    repository_id: int = Field(..., gt=0)
    limit: int = Field(10, ge=1, le=50)
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0)

class EmbeddingResult(BaseModel):
    commit_id: int
    sha: str
    message: str
    author: str
    commit_date: datetime
    similarity_score: float
    files_changed: List[str]