import pytest
from pydantic import ValidationError

from backend.app.api.scraper import ScrapeRequest


def test_scrape_request_defaults_to_bounded_review_count():
    request = ScrapeRequest(product_url="https://www.trendyol.com/example-p-1")

    assert request.max_reviews == 80


def test_scrape_request_rejects_too_many_reviews():
    with pytest.raises(ValidationError):
        ScrapeRequest(
            product_url="https://www.trendyol.com/example-p-1",
            max_reviews=1000,
        )
