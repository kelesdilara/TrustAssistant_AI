from typing import Dict, List

from playwright.sync_api import Page

from backend.app.services.generic_marketplace_review_scraper_service import (
    amazon_review_url,
    scrape_generic_marketplace_reviews,
    review_url_with_path,
)


def scrape_amazon_reviews(page: Page, product_url: str, max_reviews: int = 1000) -> List[Dict]:
    return scrape_generic_marketplace_reviews(
        page=page,
        product_url=product_url,
        platform="amazon",
        max_reviews=max_reviews,
        review_url_candidates=[
            amazon_review_url(product_url),
            review_url_with_path(product_url, "#customerReviews"),
            product_url,
        ],
        extra_card_selectors=[
            "[data-hook='review']",
            ".review",
            "#cm-cr-dp-review-list [data-hook='review']",
        ],
        extra_text_selectors=[
            "[data-hook='review-body']",
            ".review-text-content",
        ],
    )
