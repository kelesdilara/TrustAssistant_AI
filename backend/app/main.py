from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.analysis import router as analysis_router
from backend.app.api.auth import router as auth_router
from backend.app.api.scraper import router as scraper_router
from backend.app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="TrustAssistant AI",
    description="AI destekli alisveris guven analiz sistemi",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(scraper_router)


@app.get("/")
def root():
    return {"message": "TrustAssistant AI backend is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
