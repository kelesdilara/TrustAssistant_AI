from typing import Dict, List

from playwright.sync_api import Page

from backend.app.services.generic_marketplace_review_scraper_service import (
    scrape_generic_marketplace_reviews,
    review_url_with_path,
)


def scrape_n11_reviews(page: Page, product_url: str, max_reviews: int = 1000) -> List[Dict]:
    paged_urls = [
        review_url_with_path(product_url, f"?pg={page_no}#yorumlar")
        for page_no in range(1, min(35, (max_reviews // 10) + 2))
    ]
    return scrape_generic_marketplace_reviews(
        page=page,
        product_url=product_url,
        platform="n11",
        max_reviews=max_reviews,
        review_url_candidates=[
            product_url,
            review_url_with_path(product_url, "#yorumlar"),
            review_url_with_path(product_url, "/yorumlar"),
            *paged_urls,
        ],
        extra_card_selectors=[
            ".reviewList .review",
            ".customerReview",
            ".commentList",
            ".comment",
            "[class*='Review']",
            "[class*='review']",
            "[class*='comment']",
        ],
        extra_text_selectors=[
            ".reviewText",
            ".review-text",
            ".commentText",
            ".comment-text",
            "[class*='reviewText']",
            "[class*='commentText']",
        ],
    )
