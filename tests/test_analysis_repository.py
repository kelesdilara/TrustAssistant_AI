from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.database import Base
from backend.app.models.analysis import Analysis
from backend.app.models.product import Product
from backend.app.services.analysis_repository import (
    list_recent_analyses,
    save_analysis_result,
)


def test_save_analysis_result_without_db_returns_zero():
    assert save_analysis_result(None, {"overall_trust_score": 80}) == 0


def test_list_recent_analyses_without_db_returns_empty_list():
    assert list_recent_analyses(None) == []


def test_analysis_history_can_be_filtered_by_user_id():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()

    try:
        first_product = Product(name="First product")
        second_product = Product(name="Second product")
        db.add_all([first_product, second_product])
        db.flush()
        db.add_all(
            [
                Analysis(
                    product_id=first_product.id,
                    user_id=10,
                    overall_trust_score=92,
                    final_recommendation="Alinir",
                    analysis_payload={"product_name": "First product"},
                ),
                Analysis(
                    product_id=second_product.id,
                    user_id=20,
                    overall_trust_score=55,
                    final_recommendation="Dikkat",
                    analysis_payload={"product_name": "Second product"},
                ),
            ]
        )
        db.commit()

        history = list_recent_analyses(db, user_id=10)

        assert len(history) == 1
        assert history[0]["product_name"] == "First product"
        assert history[0]["overall_trust_score"] == 92
    finally:
        db.close()
