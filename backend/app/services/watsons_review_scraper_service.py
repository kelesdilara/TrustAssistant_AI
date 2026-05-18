from typing import Dict, List

from playwright.sync_api import Page

from backend.app.services.generic_marketplace_review_scraper_service import (
    scrape_generic_marketplace_reviews,
    review_url_with_path,
)


def scrape_watsons_reviews(page: Page, product_url: str, max_reviews: int = 1000) -> List[Dict]:
    return scrape_generic_marketplace_reviews(
        page=page,
        product_url=product_url,
        platform="watsons",
        max_reviews=max_reviews,
        review_url_candidates=[
            product_url,
            review_url_with_path(product_url, "#reviews"),
            review_url_with_path(product_url, "#yorumlar"),
        ],
    )
