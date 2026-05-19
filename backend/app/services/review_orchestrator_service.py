from typing import Callable, Dict, List

from playwright.sync_api import Page

from backend.app.services.amazon_review_scraper_service import scrape_amazon_reviews
from backend.app.services.ebebek_review_scraper_service import scrape_ebebek_reviews
from backend.app.services.gratis_review_scraper_service import scrape_gratis_reviews
from backend.app.services.hepsiburada_review_scraper_service import scrape_hepsiburada_reviews
from backend.app.services.lcwaikiki_review_scraper_service import scrape_lcwaikiki_reviews
from backend.app.services.mediamarkt_review_scraper_service import scrape_mediamarkt_reviews
from backend.app.services.n11_review_scraper_service import scrape_n11_reviews
from backend.app.services.teknosa_review_scraper_service import scrape_teknosa_reviews
from backend.app.services.trendyol_review_scraper_service import scrape_trendyol_reviews
from backend.app.services.vatan_review_scraper_service import scrape_vatan_reviews
from backend.app.services.watsons_review_scraper_service import scrape_watsons_reviews


REVIEW_SCRAPERS: dict[str, tuple[str, Callable]] = {
    "trendyol.com": ("trendyol", scrape_trendyol_reviews),
    "hepsiburada.com": ("hepsiburada", scrape_hepsiburada_reviews),
    "n11.com": ("n11", scrape_n11_reviews),
    "amazon.com.tr": ("amazon", scrape_amazon_reviews),
    "teknosa.com": ("teknosa", scrape_teknosa_reviews),
    "e-bebek.com": ("ebebek", scrape_ebebek_reviews),
    "lcwaikiki.com": ("lcwaikiki", scrape_lcwaikiki_reviews),
    "lcw.com": ("lcwaikiki", scrape_lcwaikiki_reviews),        # lcw.com alias
    "gratis.com": ("gratis", scrape_gratis_reviews),
    "watsons.com.tr": ("watsons", scrape_watsons_reviews),
    "mediamarkt.com.tr": ("mediamarkt", scrape_mediamarkt_reviews),
    "vatanbilgisayar.com": ("vatan", scrape_vatan_reviews),
}


def collect_reviews_from_sources(
    page: Page,
    product_url: str | None = None,
    product_name: str | None = None,
    max_reviews_per_source: int = 80,
) -> dict:
    all_reviews: List[Dict] = []
    sources: List[str] = []

    if product_url:
        lower_url = product_url.lower()
        for domain, (source_name, scraper) in REVIEW_SCRAPERS.items():
            if domain not in lower_url:
                continue

            reviews = scraper(
                page=page,
                product_url=product_url,
                max_reviews=max_reviews_per_source,
            )
            _extend_source(all_reviews, sources, reviews, source_name)
            break

    deduped_reviews = _dedupe_reviews(all_reviews)
    return {
        "reviews": deduped_reviews,
        "review_count": len(deduped_reviews),
        "review_sources": sources,
    }


def _extend_source(
    all_reviews: List[Dict],
    sources: List[str],
    reviews: List[Dict],
    source_name: str,
) -> None:
    if reviews:
        all_reviews.extend(reviews)
        if source_name not in sources:
            sources.append(source_name)


def _dedupe_reviews(reviews: List[Dict]) -> List[Dict]:
    seen = set()
    result = []

    for review in reviews:
        comment = str(review.get("comment") or "").strip()
        if not comment:
            continue

        key = " ".join(comment.lower().split())
        if key in seen:
            continue

        seen.add(key)
        result.append(review)

    return result
