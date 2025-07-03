from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
import uvicorn

app=FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG
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

if __name__ =="__main__":
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)