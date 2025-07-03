from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class AnalysisType(str, Enum):
    STRUCTURE ="structure"
    QUALITY ="quality"
    FULL ="full"

class AnalysisStatus(str, Enum):
    PENDING ="pending"
    PROCESSING ="processing"
    COMPLETED ="completed"
    FAILED ="failed"

class Anaylsis(BaseModel):
    """model analysis"""
    id: Optional[int] = None
    repository_id: int =Field(..., gt=0)
    analysis_type: AnalysisType = AnalysisType.FULL
    status: AnalysisStatus = AnalysisStatus.PENDING

    #results
    results: Optional[Dict[str, Any]] =None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True

