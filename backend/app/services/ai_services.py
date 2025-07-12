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
        