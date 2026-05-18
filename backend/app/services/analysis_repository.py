import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.analysis import Analysis
from backend.app.models.product import Product


logger = logging.getLogger(__name__)


def save_analysis_result(
    db: Session | None,
    result: dict[str, Any],
    user_id: int | None = None,
) -> int:
    if db is None:
        return 0

    try:
        product = Product(
            name=result.get("product_name"),
            url=result.get("product_url"),
            seller_name=result.get("seller_name"),
            source_platform=_first_source(result.get("review_sources")),
        )
        db.add(product)
        db.flush()

        analysis = Analysis(
            product_id=product.id,
            user_id=user_id,
            overall_trust_score=result.get("overall_trust_score", 0),
            final_recommendation=result.get("final_recommendation", ""),
            product_summary=result.get("product_summary"),
            review_analysis=result.get("review_analysis"),
            seller_analysis=result.get("seller_analysis"),
            discount_analysis=result.get("discount_analysis"),
            risk_factors=result.get("risk_factors", []),
            analysis_payload=result,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return int(analysis.id)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.warning("Analysis result could not be persisted: %s", exc)
        return 0


def list_recent_analyses(
    db: Session | None,
    limit: int = 20,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    if db is None:
        return []

    try:
        query = db.query(Analysis)
        if user_id is not None:
            query = query.filter(Analysis.user_id == user_id)
        rows = query.order_by(Analysis.created_at.desc()).limit(max(1, min(limit, 100))).all()
    except SQLAlchemyError as exc:
        logger.warning("Analysis history could not be loaded: %s", exc)
        return []

    return [_history_item(row) for row in rows]


def _history_item(analysis: Analysis) -> dict[str, Any]:
    payload = analysis.analysis_payload or {}
    return {
        "analysis_id": analysis.id,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
        "product_name": payload.get("product_name") or analysis.product_summary,
        "product_url": payload.get("product_url"),
        "seller_name": payload.get("seller_name"),
        "overall_trust_score": analysis.overall_trust_score,
        "final_recommendation": analysis.final_recommendation,
        "review_count": payload.get("review_count", 0),
        "complaint_count": payload.get("complaint_count", 0),
        "price_sources": payload.get("price_sources", []),
    }


def _first_source(value: Any) -> str | None:
    if isinstance(value, list) and value:
        return str(value[0])
    return None
