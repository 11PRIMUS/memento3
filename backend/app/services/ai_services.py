import google.generativeai as genai
from app.core.config import settings
from app.core.logging import get_logger
from app.models.embedding import EmbeddingResult
from app.schemas.analysis import AnalysisResponse, Commit_refrence
from typing import List, Dict, Any, Optional
import asyncio
import time
from datetime import datetime, timezone

logger=get_logger(__name__)

class AISerive:
    def __init__(self):
        self.model_name=settings.GEMINI_MODEL
        self.max_tokens=settings.MAX_TOKENS
        self.temperature = settings.TEMPERATURE
        
        #gemini config
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required")
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        try:
            self.model =genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=self.max_tokens,
                    temperature=self.temperature
                )
            )
            logger.info(" ai service initialised", model=self.model_name)
        except Exception as e:
            logger.error("Failed to initialize AI service", error=str(e))
            raise  
        
    def commit_context(self, commits: List[EmbeddingResult]) -> str:
        if not commits:
            return "No relevant commits found."
        
        context_parts = []
        for i, commit in enumerate(commits, 1):
            commit_info = [
                f"Commit {i}:",
                f"  SHA: {commit.sha}",
                f"  Author: {commit.author}",
                f"  Date: {commit.commit_date.strftime('%Y-%m-%d %H:%M:%S')}",
                f"  Message: {commit.message}",
                f"  Similarity Score: {commit.similarity_score:.2f}",
                f"  Changes: +{commit.additions} -{commit.deletions}",
            ]
            
            if commit.files_changed:
                files_str = ", ".join(commit.files_changed[:5])
                if len(commit.files_changed) > 5:
                    files_str += f" and {len(commit.files_changed) - 5} more files"
                commit_info.append(f"  Files: {files_str}")
            
            context_parts.append("\n".join(commit_info))
        
        return "\n\n".join(context_parts)
    
    def analysisP(self, question:str, context:str, repo_id:int)-> str:
        return f"""You are MementoAI, an expert code archaeologist and repository analyst. Your task is to analyze commit history and provide insightful answers about code evolution, patterns, and development practices.

REPOSITORY ANALYSIS REQUEST:
Repository ID: {repo_id}
Question: "{question}"

RELEVANT COMMIT HISTORY:
{context}

ANALYSIS INSTRUCTIONS:
1. Analyze the provided commits in relation to the specific question asked
2. Look for patterns, trends, and significant changes across the commits
3. Consider the temporal sequence of changes and their impact
4. Focus on code quality, architecture decisions, bug fixes, features, and technical debt
5. Provide specific examples from the commits when possible
6. Be technical but accessible in your explanations

RESPONSE FORMAT:
Provide a comprehensive analysis that:
- Directly answers the question based on the commit evidence
- Identifies key patterns and trends in the code changes
- References specific commits with their SHA when relevant
- Explains the technical implications and business impact
- Suggests insights about development practices or code quality
- Maintains a professional, analytical tone

If the commits don't contain enough information to fully answer the question, explain what you can determine and suggest what additional information might be helpful.

ANALYSIS:"""
    async def analyze_commits(self, question:str,relevant_commits: List[EmbeddingResult], repo_id:int)-> AnalysisResponse:
        start_time= time.time
        try:
            logger.info("starting ai analysis", repo_id = repo_id, commit_count=len(relevant_commits), question_length=len(question))
            #context
            context=self.commit_context(relevant_commits)
            prompt=self.analysisP(question, context, repo_id)

            if settings.DEBUG:
                logger.debug("AI prompt created",prompt_length=len(prompt))

            response =await self.generate_retry(prompt)
            confidence_score=self.calculate_confidence(relevant_commits, response)

            Commit_refrence=[]
            for commit in relevant_commits:
                commit_ref= Commit_refrence(
                    sha=commit.sha,
                    message=commit.message,
                    author=commit.author,
                    commit_date=commit.commit_date,
                    similarity_score=commit.similarity_score,
                    files_changed=commit.files_changed,
                    additions=commit.additions,
                    deletions=commit.deletions
                )
                Commit_refrence.append(commit_ref)
            
            processing_time = time.time() - start_time
            
            logger.info("AI analysis completed", repo_id=repo_id, 
                       processing_time=processing_time, confidence=confidence_score)
            
            return AnalysisResponse(
                question=question,
                answer=response,
                relevant_commits=Commit_refrence,
                confidence_score=confidence_score,
                processing_time=processing_time,
                repository_id=repo_id
            )
            
        except Exception as e:
            logger.error("AI analysis failed", repo_id=repo_id, error=str(e))
            #fallback response
            return AnalysisResponse(
                question=question,
                answer=f"sorry i can't get it, try again: {str(e)}. Please try again or rephrase your question.",
                relevant_commits=[],
                confidence_score=0.0,
                processing_time=time.time() - start_time,
                repository_id=repo_id
            )
    async def generate_retry(self, prompt: str, max_retries: int = 3) -> str:
        for attempt in range(max_retries):
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, self.model.generate_content, prompt
                )
                
                if response.text:
                    return response.text.strip()
                else:
                    raise Exception("empty response from AI model")
                    
            except Exception as e:
                logger.warning(f"AI generation attempt {attempt + 1} failed", error=str(e))
                if attempt == max_retries - 1:
                    raise Exception(f"AI generation failed after {max_retries} attempts: {str(e)}")
                await asyncio.sleep(2 ** attempt)
        
        raise Exception(" AI geeneration failed")

    def calculate_confidence  (self, commits:List[EmbeddingResult], response:str)-> float:
        if not commits or not response:
            return 0.0
        
        #base confidence on similarity scores
        avg_similarity = sum(commit.similarity_score for commit in commits) / len(commits)
        commit_count_factor = min(len(commits) / 10, 1.0)
        
        #response quality factor
        response_length_factor =min(len(response) / 500, 1.0) 
        
        technical_keywords = [
            'function', 'class', 'method', 'variable', 'algorithm', 'pattern',
            'architecture', 'design', 'implementation', 'refactor', 'optimization',
            'bug', 'fix', 'feature', 'enhancement', 'security', 'performance'
        ]
        
        technical_score = sum(1 for keyword in technical_keywords 
                            if keyword.lower() in response.lower()) / len(technical_keywords)
        
        confidence = (
            avg_similarity * 0.4 +
            commit_count_factor * 0.3 +
            response_length_factor * 0.2 +
            technical_score * 0.1
        )
        
        return min(max(confidence, 0.0), 1.0)     