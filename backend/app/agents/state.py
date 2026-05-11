from typing import List, Optional, TypedDict


class ReviewItem(TypedDict, total=False):
    platform: str
    rating: int
    comment: str
    date: str
    username: str


class AnalysisState(TypedDict, total=False):
    product_url: Optional[str]
    product_name: Optional[str]
    seller_name: Optional[str]
    platform_name: Optional[str]

    reviews: List[ReviewItem]

    fake_review_score: int
    seller_score: int
    price_risk_score: int

    review_analysis: str
    seller_analysis: str
    discount_analysis: str

    overall_trust_score: int
    final_recommendation: str
    product_summary: str
    risk_factors: List[str]