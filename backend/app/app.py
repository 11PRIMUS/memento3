from fastapi import FastAPI

app=FastAPI(title="Memento server", version="0.1")

@app.get("/")
async def root():
    return {"message":" memento server api"}

@app.get("/health")
async def health_check():
    return {"status":"ok"}