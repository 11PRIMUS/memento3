import google.generativeai as genai
from app.core.config import settings
from app.core.logging import get_logger
from app.models.embedding import EmbeddingResult
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
    
    def analysis(self, question:str, context:str, repo_id:int)-> str:
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
