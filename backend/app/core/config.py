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
    GITHUB_API_KEY :str
    
    
    #CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        case_senstive =True

settings = Settings()