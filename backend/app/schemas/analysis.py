from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class AnalysisRequest(BaseModel):
    product_url: Optional[str] = Field(
        default=None,
        description="Urun linki. Sadece urun adiyla arama yapmak icin bos birakin.",
        examples=[
            "https://www.trendyol.com/mad-parfum/mad-v109-selective-50-ml-kadin-parfum-p-663751330"
        ],
    )
    product_name: Optional[str] = Field(
        default=None,
        description="Urun adi. Link bos ise marketplace linkleri otomatik aranir.",
        examples=["iphone 15"],
    )
    seller_name: Optional[str] = None
    search_mode: Literal["fast", "wide"] = Field(
        default="fast",
        description="Urun adi aramasinda fast 4 ana marketplace, wide tum marketplace listesini kullanir.",
    )

    @field_validator("product_url", "product_name", "seller_name", "search_mode", mode="before")
    @classmethod
    def normalize_empty_inputs(cls, value):
        if value is None:
            return None

        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned == "" or cleaned.lower() in {"string", "null", "none"}:
                return None
            return cleaned

        return value

    @model_validator(mode="after")
    def validate_product_input(self):
        if not self.product_url and not self.product_name:
            raise ValueError("product_url veya product_name alanlarindan en az biri girilmelidir.")

        if self.product_url and not self.product_url.startswith(("http://", "https://")):
            raise ValueError("product_url gecerli bir http/https linki olmalidir.")

        return self


class AnalysisResponse(BaseModel):
    analysis_id: int
    analysis_scope: Optional[str] = None
    overall_trust_score: int
    final_recommendation: str
    product_summary: str
    review_analysis: str
    seller_analysis: str
    discount_analysis: str
    risk_factors: List[str]

    review_count: int
    review_sources: List[str]
    source_review_counts: dict = Field(default_factory=dict)
    source_links: dict = Field(default_factory=dict)
    review_sample_target: int = 0
    review_sample_minimum: int = 0
    complaints: List[dict] = Field(default_factory=list)
    complaint_count: int = 0
    complaint_sources: List[str] = Field(default_factory=list)
    complaint_scope: Optional[str] = None
    complaint_query: Optional[str] = None
    price_sources: List[str] = Field(default_factory=list)
    price_history_source: Optional[str] = None
    price_history_days: int = 0
    price_history_is_estimated: bool = False
    current_market_prices: List[dict] = Field(default_factory=list)
    price_search_url: Optional[str] = None
    price_search_urls: dict = Field(default_factory=dict)


class AnalysisHistoryItem(BaseModel):
    analysis_id: int
    created_at: Optional[str] = None
    product_name: Optional[str] = None
    product_url: Optional[str] = None
    seller_name: Optional[str] = None
    overall_trust_score: int
    final_recommendation: str
    review_count: int = 0
    complaint_count: int = 0
    price_sources: List[str] = Field(default_factory=list)
