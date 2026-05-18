from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.agents.graph import build_analysis_graph
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
    user_id = current_user.id if current_user else None
    return list_recent_analyses(db, limit=limit, user_id=user_id)


@router.post("/", response_model=AnalysisResponse)
def create_analysis(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    graph = build_analysis_graph()

    result = graph.invoke(
        {
            "product_url": request.product_url,
            "product_name": request.product_name,
            "seller_name": request.seller_name,
            "search_mode": request.search_mode,
        }
    )
    user_id = current_user.id if current_user else None
    analysis_id = save_analysis_result(db, result, user_id=user_id)

    return AnalysisResponse(
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
