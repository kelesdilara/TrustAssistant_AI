import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.agents.graph import build_analysis_graph
from backend.app.api.analysis import router as analysis_router
from backend.app.api.auth import router as auth_router
from backend.app.api.scraper import router as scraper_router
from backend.app.core.config import settings
from backend.app.db.init_db import init_db


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    app.state.analysis_graph = build_analysis_graph()

    try:
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
        app.state.redis = redis_client
        logger.info("Redis bağlantısı kuruldu.")
    except Exception as exc:
        logger.warning("Redis bağlanamadı, önbellekleme devre dışı: %s", exc)
        app.state.redis = None

    yield

    if app.state.redis:
        await app.state.redis.aclose()


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
