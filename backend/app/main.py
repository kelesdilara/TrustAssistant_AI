from fastapi import FastAPI
from backend.app.db.init_db import init_db
from backend.app.api.analysis import router as analysis_router

app = FastAPI(
    title="TrustAssistant AI",
    description="AI destekli alışveriş güven analiz sistemi",
    version="0.1.0",
)

@app.on_event("startup")
def startup_event():
    init_db()

app.include_router(analysis_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "TrustAssistant AI backend is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}