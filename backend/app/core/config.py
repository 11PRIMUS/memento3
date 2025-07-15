from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    #app settings
    APP_NAME: str = "MementoAI server"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    #server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    #supabase
    SUPABASE_URL: str 
    SUPABASE_KEY: str 

    #github api's
    GITHUB_TOKEN:Optional[str] =None
    
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-1.5-flash"
    MAX_TOKENS: int=1000
    TEMPERATURE: float =0.7
    
    #embedding model
    EMBEDDING_MODEL: str ="sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int=384
    
    #CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        case_senstive =True

settings = Settings()