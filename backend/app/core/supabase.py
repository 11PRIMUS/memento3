from supabase import create_client, Client
from app.core.config import settings
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)

class SupabaseManager:
    _instance: Optional['SupabaseManager']=None
    _client: Optional[Client] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance =super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self.initialize_client()

    def intitialize_client(self):
        try:
            if not settings.SUPABASE_URL:
                raise ValueError("supbabse url is required")
            
            if not settings.SUPABASE_KEY:
                raise ValueError("supabase key is required")
            
            self._client =create_client(
                supabase_url=settings.SUPABASE_URL,
                supabase_key=settings.SUPABASE_KEY
            )
            
            logger.info("Supabase client initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Supabase client", error=str(e))
            raise
            

    @classmethod
    def get_client(cls) -> Client:
        instance=cls()
        if instance._client is None:
            raise Exception("sp client not initialized")
        return instance._client
    
    @classmethod
    def test_connection(cls) -> bool:
        try:
            client = cls.get_client()
            response = client.table('repositories').select('id').limit(1).execute()
            logger.info("Supabase connection test successful")
            return True
        except Exception as e:
            logger.error("Supabase connection test failed", error=str(e))
            return False
        
@lru_cache()
def get_supabase() -> Client:
    """FastAPI dependency to get Supabase client"""
    return SupabaseManager.get_client()

class SupabaseHealthCheck:
    """Health check utilities for Supabase"""
    
    @staticmethod
    async def check_database_connection() -> dict:
        """Check database connection health"""
        try:
            client = SupabaseManager.get_client()
            start_time = asyncio.get_event_loop().time()
            response = client.table('repositories').select('count').execute()
            end_time = asyncio.get_event_loop().time()
            
            response_time = (end_time - start_time) * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "url": settings.SUPABASE_URL,
                "tables_accessible": True
            }
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "url": settings.SUPABASE_URL,
                "tables_accessible": False
            }

DATABASE_SCHEMA = """
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Repositories table
CREATE TABLE IF NOT EXISTS repositories (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(500) NOT NULL UNIQUE,
    owner VARCHAR(100),
    description TEXT,
    default_branch VARCHAR(50) DEFAULT 'main',
    
    -- GitHub metadata
    github_id BIGINT,
    stars INTEGER DEFAULT 0,
    forks INTEGER DEFAULT 0,
    language VARCHAR(50),
    
    -- Analysis status
    status VARCHAR(20) DEFAULT 'pending',
    total_commits INTEGER DEFAULT 0,
    indexed_commits INTEGER DEFAULT 0,
    last_analyzed_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Commits table
CREATE TABLE IF NOT EXISTS commits (
    id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    sha VARCHAR(40) NOT NULL UNIQUE,
    message TEXT NOT NULL,
    author VARCHAR(255),
    author_email VARCHAR(255),
    commit_date TIMESTAMPTZ NOT NULL,
    
    -- Stats
    additions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    files_changed JSONB DEFAULT '[]',
    
    -- Embedding info
    embedding_id VARCHAR(100),
    embedding_created_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Embeddings table
CREATE TABLE IF NOT EXISTS embeddings (
    id BIGSERIAL PRIMARY KEY,
    commit_id BIGINT NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    embedding_vector VECTOR(384),
    model_name VARCHAR(100),
    text_content TEXT,
    embedding_type VARCHAR(50) DEFAULT 'commit_message',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);
-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_repositories_status ON repositories(status);
CREATE INDEX IF NOT EXISTS idx_repositories_url ON repositories(url);
CREATE INDEX IF NOT EXISTS idx_commits_repository_id ON commits(repository_id);
CREATE INDEX IF NOT EXISTS idx_commits_sha ON commits(sha);
CREATE INDEX IF NOT EXISTS idx_commits_date ON commits(commit_date DESC);
CREATE INDEX IF NOT EXISTS idx_embeddings_commit_id ON embeddings(commit_id);

-- Vector search function
CREATE OR REPLACE FUNCTION search_similar_commits(
    query_embedding VECTOR(384),
    repo_id BIGINT,
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    commit_id BIGINT,
    sha VARCHAR(40),
    message TEXT,
    author VARCHAR(255),
    commit_date TIMESTAMPTZ,
    additions INT,
    deletions INT,
    files_changed JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id,
        c.sha,
        c.message,
        c.author,
        c.commit_date,
        c.additions,
        c.deletions,
        c.files_changed,
        1 - (e.embedding_vector <=> query_embedding) AS similarity
    FROM commits c
    JOIN embeddings e ON c.id = e.commit_id
    WHERE c.repository_id = repo_id
    AND 1 - (e.embedding_vector <=> query_embedding) > match_threshold
    ORDER BY e.embedding_vector <=> query_embedding
    LIMIT match_count;
END;
$$;
"""

async def initialize_database():
    logger.info("db schema :")
    print("\n" + "="*50)
    print("EXECUTE THIS SQL IN YOUR SUPABASE DASHBOARD:")
    print("="*50)
    print(DATABASE_SCHEMA)
    print("="*50 + "\n")
    return DATABASE_SCHEMA