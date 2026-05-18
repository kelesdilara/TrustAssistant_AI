from fastapi import APIRouter
from pydantic import BaseModel, Field, HttpUrl
from starlette.concurrency import run_in_threadpool

from backend.app.services.scraper_service import scrape_product_data_sync

router = APIRouter(prefix="/scraper", tags=["Scraper"])


class ScrapeRequest(BaseModel):
    product_url: HttpUrl
    max_reviews: int = Field(default=80, ge=1, le=200)


@router.post("/product")
async def scrape_product(request: ScrapeRequest):
    return await run_in_threadpool(
        scrape_product_data_sync,
        str(request.product_url),
        request.max_reviews,
    )
