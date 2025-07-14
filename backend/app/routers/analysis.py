from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client
from typing import Optional

from app.core.supabase import get_supabase
from app.core.logging import get_logger
from app.services.supabase_service import SupabaseService
from app.services.embedding_service import EmbeddingService
from app.services.ai_services import AISerive
from app.schemas.analysis import (
    AnalysisRequest, AnalysisResponse, AnalysisHistory, AnalysisHistoryList
)



logger = get_logger(__name__)
router=APIRouter()

def get_supabaseSerive(client: Client= Depends(get_supabase))->SupabaseService:
    return SupabaseService (client)

def get_embeddingSerive(client: Client=Depends(get_supabase))->EmbeddingService:
    return EmbeddingService(client)

def get_aiService()-> AISerive:
    return AISerive()

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_repo(
    request: AnalysisRequest,
    supabase_Service: SupabaseService= Depends(get_supabaseSerive),
    embedding_service: EmbeddingService= Depends(get_embeddingSerive),
    ai_serive: AISerive= Depends(get_aiService)
):
    #anlaysis based on question
    try:
        logger.info("starting analysis", repo_id=request.repository_id, question_length=len(request.questions))
        repository = await supabase_Service.get_repo(request.repository_id)
        if not repository:
            raise HTTPException(status_code=404, detail=" repository not found")
        if repository.status != "completed":
            raise HTTPException(
                status_code=400, 
                detail=f"Repository is not ready for analysis. Status: {repository.status}"
            )
        #search for similar commits
        similar_commits = await embedding_service.similar_commits(
            query=request.questions,
            repo_id=request.repository_id,
            limit=request.max_commits or 10,
            threshold=request.similarity_t or 0.7
        )
        if not similar_commits:
            logger.warning("No similar commits found", repo_id=request.repository_id)
            return AnalysisResponse(
                question=request.questions,
                answer="I couldn't find any relevant commits to answer your question. This might be because:\n\n1. The repository hasn't been fully indexed yet\n2. Your question doesn't match the available commit history\n3. The similarity threshold is too high\n\nTry rephrasing your question or check if the repository indexing is complete.",
                relevant_commits=[],
                confidence_score=0.0,
                processing_time=0.0,
                repository_id=request.repository_id
            )
        analysis_response = await ai_serive.analyze_commits(
            question=request.questions,
            relevant_commits=similar_commits,
            repo_id=request.repository_id
        )
        
        try:
            await store_analysis_session(
                supabase_Service,
                analysis_response
            )
        except Exception as e:
            logger.warning("failed to store analysis session", error=str(e))
        
        logger.info("Analysis completed", repo_id=request.repository_id, 
                   confidence=analysis_response.confidence_score)
        
        return analysis_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in analysis", repo_id=request.repository_id, error=str(e))
        raise HTTPException(status_code=500, detail="analysis failed")

@router.get("/repository/{repo_id}/history",response_model=AnalysisHistoryList)
async def get_analysis_history(
    repo_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=50, description="Items per page"),
    supabase_service: SupabaseService = Depends(get_supabaseSerive)

):
    try:
        repository= await supabase_service.get_repo(repo_id)
        if not repository:
            raise HTTPException(status_code=404,detail="repo not found")
        logger.info("retrieved analysis history",repo_id=repo_id)
    
        return AnalysisHistoryList(
            analyses=[],
            total=0,
            page=page,
            per_page=per_page,
            has_next=False
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("error fetching analysis history", repo_id=repo_id, error=str(e))
        raise HTTPException(status_code=500, detail="failed to fetch analysis history")
    