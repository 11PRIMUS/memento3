from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.supabase import SupabaseManager, SupabaseHealthCheck, initialize_database
from app.core.logging import setup_logging, get_logger
from app.services.ai_services import AIService
from app.routers import repositories, analysis
from contextlib import asynccontextmanager
import uvicorn
from datetime import datetime, timezone

setup_logging()
logger=get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        if SupabaseManager.test_connection():
            logger.info("supabase connection established")

        else:
            logger.warning("supbabse connection test failed")
    except Exception as e:
        logger.error("supabase connection failed", error=str(e))
        
    try:
        db_ready = await initialize_database()
        if db_ready:
            logger.info("db initialization completed")
        else:
            logger.warning("db initialization had issues")
    except Exception as e:
        logger.error("DB initialzation failed", error=str(e))
    
    try:
        ai_service=AIService()
        if ai_service.test_connection():
            logger.info("AI service connection started")
        else:
            logger.warning("AI service test failed")
    except Exception as e:
        logger.error("AI service initialization failed", error=str(e))

    yield
        

app=FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(
    repositories.router,
    prefix="/api/repositories",
    tags=["repositories"]
)

app.include_router(
    analysis.router,
    prefix="/api/analysis",
    tags=["analysis"]
)

@app.get("/")
async def root():
    return {"message":settings.APP_NAME, "version":settings.VERSION ,"status":"runnning"}

@app.get("/health")
async def health_check():
    health_check={
        "status": "healthy",
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {}
    }
    #supabase
    try:
        health_check["services"]["database"]={
            "status":"connected" if SupabaseManager.test_connection() else "disconnected",
            "types":"Supabase"
            }
    except Exception as e:
        health_check["services"]["database"]={
            "status": "error",
            "error": str(e),
            "type": "Supabase"
        }
    #ai service
    try:
        ai_service = AIService()
        health_check["services"]["ai"] = {
            "status": "connected" if ai_service.test_connection() else "disconnected",
            "type": "Google Gemini",
            "model":settings.GEMINI_MODEL
        }
    except Exception as e:
        health_check["services"]["ai"] = {
            "status":"error",
            "error": str(e),
            "type": "Google Gemini"
        }
    
    service_statuses = [service["status"] for service in health_status["services"].values()]
    if "error" in service_statuses:
        health_check["status"] ="degraded"
    elif "disconnected" in service_statuses:
        health_check["status"] ="partial"
    
    return health_check

@app.get("/api/info")
async def api_info():
    return {
        "app_name":settings.APP_NAME,
        "version": settings.VERSION,
        "debug_mode": settings.DEBUG,
        "embedding_model": settings.EMBEDDING_MODEL,
        "ai_model": settings.GEMINI_MODEL,
        "supported_endpoints": {
            "repositories": "/api/repositories",
            "analysis": "/api/analysis",
            "health": "/health",
            "docs": "/docs" if settings.DEBUG else "disabled"
        }
    }

if __name__ =="__main__":
    uvicorn.run(app, host=settings.HOST, port=settings.PORT, reload=settings.DEBUG, log_config=None)