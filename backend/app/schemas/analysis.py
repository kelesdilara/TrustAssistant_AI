from typing import List, Optional

from pydantic import BaseModel, model_validator


class AnalysisRequest(BaseModel):
    product_url: Optional[str] = None
    product_name: Optional[str] = None
    seller_name: Optional[str] = None

    @model_validator(mode="after")
    def validate_product_input(self):
        if not self.product_url and not self.product_name:
            raise ValueError("product_url veya product_name alanlarından en az biri girilmelidir.")
        return self


class AnalysisResponse(BaseModel):
    analysis_id: int
    overall_trust_score: int
    final_recommendation: str
    product_summary: str
    review_analysis: str
    seller_analysis: str
    discount_analysis: str
    risk_factors: List[str]