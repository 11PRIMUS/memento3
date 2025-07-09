from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.supabase import SupabaseManager, SupabaseHealthCheck, initialize_database
from app.core.logging import setup_logging, get_logger
from contextlib import asynccontextmanager
import uvicorn

setup_logging()
logger=get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        if SupabaseManager.test_connection():
            logger.info("supabase connection success")

        else:
            logger.warnig("failed supabase connection")
    except Exception as e:
        logger.error("failed to initialize supabase")
        await initialize_database()

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

@app.get("/")
async def root():
    return {"message":settings.APP_NAME, "version":settings.VERSION}

@app.get("/health")
async def health_check():
    return {"status":"ok", "version":settings.VERSION}

    # db_health =await SupabaseHealthCheck.check_database_connection()
    # health_status["services"]["database"]=db_health

    # if db_health["status"]!="healthy":
    #     health_status["status"]="degraded"

    # return health_status

if __name__ =="__main__":
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)