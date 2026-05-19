import asyncio
import functools
import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from backend.app.api.deps import get_optional_current_user
from backend.app.db.database import get_db
from backend.app.models.user import User
from backend.app.schemas.analysis import (
    AnalysisHistoryItem,
    AnalysisRequest,
    AnalysisResponse,
)
from backend.app.services.analysis_repository import (
    list_recent_analyses,
    save_analysis_result,
)

CACHE_TTL_SECONDS = 3600

router = APIRouter(
    prefix="/analysis",
    tags=["Analysis"],
)


@router.get("/history", response_model=list[AnalysisHistoryItem])
def get_analysis_history(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    if current_user is None:
        return []

    user_id = current_user.id if current_user else None
    return list_recent_analyses(db, limit=limit, user_id=user_id)


@router.post("/", response_model=AnalysisResponse)
async def create_analysis(
    req: Request,
    request: AnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    redis = getattr(req.app.state, "redis", None)
    cache_key = _cache_key(request)

    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                return AnalysisResponse(**json.loads(cached))
        except Exception:
            pass

    graph = req.app.state.analysis_graph
    initial_state = {
        "product_url": request.product_url,
        "product_name": request.product_name,
        "seller_name": request.seller_name,
        "search_mode": request.search_mode,
    }

    loop = asyncio.get_running_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, functools.partial(graph.invoke, initial_state)),
            timeout=180.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Analiz zaman aşımına uğradı (3 dakika). Lütfen tekrar deneyin.")

    user_id = current_user.id if current_user else None
    analysis_id = save_analysis_result(db, result, user_id=user_id)

    response = AnalysisResponse(
        analysis_id=analysis_id,
        analysis_scope=result.get("analysis_scope"),
        overall_trust_score=result["overall_trust_score"],
        final_recommendation=result["final_recommendation"],
        product_summary=result["product_summary"],
        review_analysis=result["review_analysis"],
        seller_analysis=result["seller_analysis"],
        discount_analysis=result["discount_analysis"],
        risk_factors=result["risk_factors"],
        review_count=result.get("review_count", 0),
        review_sources=result.get("review_sources", []),
        source_review_counts=result.get("source_review_counts", {}),
        source_links=result.get("source_links", {}),
        review_sample_target=result.get("review_sample_target", 0),
        review_sample_minimum=result.get("review_sample_minimum", 0),
        complaints=result.get("complaints", []),
        complaint_count=result.get("complaint_count", 0),
        complaint_sources=result.get("complaint_sources", []),
        complaint_scope=result.get("complaint_scope"),
        complaint_query=result.get("complaint_query"),
        price_sources=result.get("price_sources", []),
        price_history_source=result.get("price_history_source"),
        price_history_days=result.get("price_history_days", 0),
        price_history_is_estimated=result.get("price_history_is_estimated", False),
        current_market_prices=result.get("current_market_prices", []),
        price_search_url=result.get("price_search_url"),
        price_search_urls=result.get("price_search_urls", {}),
    )

    if redis:
        try:
            await redis.setex(cache_key, CACHE_TTL_SECONDS, response.model_dump_json())
        except Exception:
            pass

    return response


def _cache_key(request: AnalysisRequest) -> str:
    raw = "|".join([
        (request.product_url or "").strip().lower().rstrip("/"),
        (request.product_name or "").strip().lower(),
        (request.seller_name or "").strip().lower(),
        request.search_mode,
    ])
    return "analysis:" + hashlib.sha256(raw.encode()).hexdigest()
