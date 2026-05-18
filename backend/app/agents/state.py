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
    search_mode: str
    analysis_scope: Optional[str]
    price: Optional[str]

    reviews: List[ReviewItem]
    complaints: list
    price_history: list
    price_sources: list
    price_history_source: Optional[str]
    price_history_days: int
    price_history_is_estimated: bool
    current_market_prices: list
    price_search_url: Optional[str]
    price_search_urls: dict
    seller_info: dict
    review_count: int
    review_sources: list
    source_review_counts: dict
    source_links: dict
    review_sample_target: int
    review_sample_minimum: int
    complaint_count: int
    complaint_sources: list
    complaint_scope: Optional[str]
    complaint_query: Optional[str]
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
