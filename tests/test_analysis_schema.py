import pytest
from pydantic import ValidationError

from backend.app.schemas.analysis import AnalysisRequest


def test_analysis_request_ignores_swagger_string_placeholder():
    request = AnalysisRequest(product_url="string", product_name="iphone 15")

    assert request.product_url is None
    assert request.product_name == "iphone 15"


def test_analysis_request_rejects_placeholder_without_product_name():
    with pytest.raises(ValidationError):
        AnalysisRequest(product_url="string")


def test_analysis_request_rejects_invalid_product_url():
    with pytest.raises(ValidationError):
        AnalysisRequest(product_url="iphone-15", product_name=None)


def test_analysis_request_accepts_wide_search_mode():
    request = AnalysisRequest(product_name="iphone 15", search_mode="wide")

    assert request.search_mode == "wide"


def test_analysis_request_rejects_unknown_search_mode():
    with pytest.raises(ValidationError):
        AnalysisRequest(product_name="iphone 15", search_mode="all")
