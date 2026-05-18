from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func

from backend.app.db.database import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    overall_trust_score = Column(Integer, nullable=False)
    final_recommendation = Column(String, nullable=False)

    product_summary = Column(String, nullable=True)
    review_analysis = Column(String, nullable=True)
    seller_analysis = Column(String, nullable=True)
    discount_analysis = Column(String, nullable=True)

    risk_factors = Column(JSON, nullable=True)
    analysis_payload = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
