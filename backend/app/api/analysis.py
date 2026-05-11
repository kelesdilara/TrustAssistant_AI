from fastapi import APIRouter

from backend.app.agents.graph import build_analysis_graph
from backend.app.schemas.analysis import AnalysisRequest, AnalysisResponse


router = APIRouter(
    prefix="/analysis",
    tags=["Analysis"],
)


@router.post("/", response_model=AnalysisResponse)
def create_analysis(request: AnalysisRequest):
    graph = build_analysis_graph()

    result = graph.invoke(
        {
            "product_url": request.product_url,
            "product_name": request.product_name,
            "seller_name": request.seller_name,
        }
    )

    return AnalysisResponse(
        analysis_id=0,
        overall_trust_score=result["overall_trust_score"],
        final_recommendation=result["final_recommendation"],
        product_summary=result["product_summary"],
        review_analysis=result["review_analysis"],
        seller_analysis=result["seller_analysis"],
        discount_analysis=result["discount_analysis"],
        risk_factors=result["risk_factors"],
    )