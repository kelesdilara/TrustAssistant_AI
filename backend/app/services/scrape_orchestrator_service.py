from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from urllib.parse import urlparse

from backend.app.services.scraper_service import scrape_product_data_sync
from backend.app.services.price_history_service import get_price_signals
from backend.app.services.seller_info_service import get_seller_info
from backend.app.services.marketplace_search_service import search_product_links
from backend.app.services.complaint_scraper_service import get_complaint_signals


logger = logging.getLogger(__name__)


ACTIVE_MARKETPLACES = [
    "hepsiburada",
    "trendyol",
    "n11",
    "amazon",
    "teknosa",
    "ebebek",
    "lcwaikiki",
    "gratis",
    "watsons",
    "mediamarkt",
    "vatan",
]

AUTO_ANALYSIS_MARKETPLACES = [
    "trendyol",
    "hepsiburada",
    "n11",
    "amazon",
]

LINK_ANALYSIS_MARKETPLACES = [
    "trendyol",
    "hepsiburada",
    "n11",
    "amazon",
    "gratis",
    "watsons",
    "teknosa",
    "mediamarkt",
]

MAX_REVIEWS_PER_SOURCE = 1000
MIN_STRONG_REVIEW_SAMPLE = 500
MAX_ANALYSIS_SOURCES = 6


def collect_all_product_data(
    product_url: str | None = None,
    product_name: str | None = None,
    seller_name: str | None = None,
    search_mode: str = "fast",
) -> dict:
    """
    1) Link girildiyse: o linkten veri çeker.
    2) Sadece ürün adı girildiyse: HB + Trendyol linklerini otomatik bulur,
       iki kaynaktan yorumları birleştirir.
    """

    # Kullanıcı link verdiyse mevcut tek kaynak akışı bozulmasın.
    if product_url:
        product_data = scrape_product_data_sync(
            product_url,
            max_reviews_per_source=MAX_REVIEWS_PER_SOURCE,
        )
        price = product_data.get("price")
        resolved_product_name = product_data.get("product_name") or product_name
        resolved_seller_name = product_data.get("seller_name") or seller_name
        source_links = _source_links_for_product_url(
            product_url=product_url,
            product_name=resolved_product_name,
        )
        original_source = _marketplace_from_url(product_url) or "source"
        links_to_scrape = {
            platform: link
            for platform, link in source_links.items()
            if platform != original_source
        }
        scrape_results = {original_source: product_data}
        scrape_results.update(_scrape_source_links(links_to_scrape))
        all_reviews, review_sources, source_review_counts, scraped_products = (
            _collect_reviews_from_scrape_results(scrape_results)
        )
        if not all_reviews:
            all_reviews = product_data.get("reviews", [])
        all_reviews = _dedupe_reviews(all_reviews)
        if not review_sources:
            review_sources = product_data.get("review_sources", [])
        for source in product_data.get("review_sources", []):
            source_review_counts.setdefault(source, product_data.get("review_count", 0))

        complaint_result = get_complaint_signals(
            seller_name=resolved_seller_name,
            product_name=resolved_product_name,
            site_name=_site_name_from_url(product_url),
        )
        seller_complaint_count = (
            complaint_result.get("complaint_count", 0)
            if complaint_result.get("complaint_scope") == "seller"
            else 0
        )
        price_result = get_price_signals(
            product_name=resolved_product_name,
            current_price_text=price,
        )

        return {
            "analysis_scope": "product_link_full",
            "product_name": resolved_product_name,
            "product_url": product_data.get("product_url") or product_url,
            "seller_name": resolved_seller_name,
            "price": price,
            "reviews": all_reviews,
            "review_count": len(all_reviews),
            "review_sources": review_sources,
            "source_review_counts": source_review_counts,
            "source_links": source_links,
            "scraped_products": scraped_products,
            "review_sample_target": MAX_REVIEWS_PER_SOURCE,
            "review_sample_minimum": MIN_STRONG_REVIEW_SAMPLE,
            "complaints": complaint_result.get("complaints", []),
            "complaint_count": complaint_result.get("complaint_count", 0),
            "complaint_sources": complaint_result.get("complaint_sources", []),
            "complaint_scope": complaint_result.get("complaint_scope"),
            "complaint_query": complaint_result.get("complaint_query"),
            "price_history": price_result.get("price_history", []),
            "price_sources": price_result.get("price_sources", []),
            "price_history_source": price_result.get("price_history_source"),
            "price_history_days": price_result.get("price_history_days", 0),
            "price_history_is_estimated": price_result.get("price_history_is_estimated", False),
            "current_market_prices": price_result.get("current_market_prices", []),
            "price_search_url": price_result.get("price_search_url"),
            "price_search_urls": price_result.get("price_search_urls", {}),
            "seller_info": get_seller_info(
                seller_name=resolved_seller_name,
                product_url=product_url,
                complaint_count=seller_complaint_count,
            ),
        }

    # Kullanıcı sadece ürün adı verdiyse otomatik linkler yalnızca yorum
    # toplamak için kullanılır; satıcı ve fiyat bağlamı link olmadan kesinleşmez.
    review_only = not seller_name
    enabled_marketplaces = (
        ACTIVE_MARKETPLACES
        if search_mode == "wide"
        else AUTO_ANALYSIS_MARKETPLACES
    )
    source_links = search_product_links(
        product_name=product_name or "",
        enabled_marketplaces=enabled_marketplaces,
        headless=True,
        per_marketplace_timeout_ms=12000,
    )

    scrape_results = _scrape_source_links(source_links)
    all_reviews, review_sources, source_review_counts, scraped_products = (
        _collect_reviews_from_scrape_results(scrape_results)
    )
    first_seller = seller_name
    best_product_name = product_name

    for platform, link in source_links.items():
        try:
            data = scrape_results.get(platform)
            if not data:
                continue

            if not best_product_name and data.get("product_name"):
                best_product_name = data.get("product_name")
        except Exception as e:
            logger.warning("Multi-source scrape error [%s]: %s", platform, e)

    all_reviews = _dedupe_reviews(all_reviews)
    complaint_result = (
        get_complaint_signals(seller_name=first_seller, product_name=None)
        if first_seller
        else _empty_complaint_result()
    )
    seller_complaint_count = (
        complaint_result.get("complaint_count", 0)
        if complaint_result.get("complaint_scope") == "seller"
        else 0
    )
    price_result = _empty_price_result()

    return {
        "analysis_scope": (
            "product_name_review_only" if review_only else "product_name_with_seller"
        ),
        "product_name": best_product_name,
        "product_url": None,
        "seller_name": first_seller,
        "price": None,
        "reviews": all_reviews,
        "review_count": len(all_reviews),
        "review_sources": review_sources,
        "source_review_counts": source_review_counts,
        "source_links": source_links,
        "scraped_products": scraped_products,
        "review_sample_target": MAX_REVIEWS_PER_SOURCE,
        "review_sample_minimum": MIN_STRONG_REVIEW_SAMPLE,
        "complaints": complaint_result.get("complaints", []),
        "complaint_count": complaint_result.get("complaint_count", 0),
        "complaint_sources": complaint_result.get("complaint_sources", []),
        "complaint_scope": complaint_result.get("complaint_scope"),
        "complaint_query": complaint_result.get("complaint_query"),
        "price_history": price_result.get("price_history", []),
        "price_sources": price_result.get("price_sources", []),
        "price_history_source": price_result.get("price_history_source"),
        "price_history_days": price_result.get("price_history_days", 0),
        "price_history_is_estimated": price_result.get("price_history_is_estimated", False),
        "current_market_prices": price_result.get("current_market_prices", []),
        "price_search_url": price_result.get("price_search_url"),
        "price_search_urls": price_result.get("price_search_urls", {}),
        "seller_info": get_seller_info(
            seller_name=first_seller,
            product_url=None,
            complaint_count=seller_complaint_count,
        ),
    }


def _dedupe_reviews(reviews: list[dict]) -> list[dict]:
    seen = set()
    cleaned = []

    for review in reviews:
        comment = str(review.get("comment") or "").strip()
        if not comment:
            continue

        key = " ".join(comment.lower().split())
        if key in seen:
            continue

        seen.add(key)
        cleaned.append(review)

    return cleaned


def _source_links_for_product_url(product_url: str, product_name: str | None) -> dict:
    original_key = _marketplace_from_url(product_url) or "source"
    source_links = {original_key: product_url}
    if not product_name:
        return source_links

    searched_links = search_product_links(
        product_name=product_name,
        enabled_marketplaces=LINK_ANALYSIS_MARKETPLACES,
        headless=True,
        per_marketplace_timeout_ms=12000,
        max_workers=6,
    )
    source_links.update(searched_links)
    source_links[original_key] = product_url
    return _limit_source_links(source_links, original_key=original_key)


def _scrape_source_links(source_links: dict[str, str]) -> dict[str, dict | None]:
    if not source_links:
        return {}

    scrape_results = {}
    with ThreadPoolExecutor(max_workers=min(4, len(source_links))) as executor:
        future_to_source = {
            executor.submit(
                scrape_product_data_sync,
                link,
                MAX_REVIEWS_PER_SOURCE,
            ): (platform, link)
            for platform, link in source_links.items()
        }

        for future in as_completed(future_to_source):
            platform, _link = future_to_source[future]
            try:
                scrape_results[platform] = future.result()
            except Exception as e:
                logger.warning("Multi-source scrape error [%s]: %s", platform, e)
                scrape_results[platform] = None

    return scrape_results


def _limit_source_links(
    source_links: dict[str, str],
    original_key: str | None = None,
) -> dict[str, str]:
    priority = [
        original_key,
        "trendyol",
        "n11",
        "gratis",
        "watsons",
        "hepsiburada",
        "amazon",
        "teknosa",
        "mediamarkt",
    ]
    result = {}

    for key in priority:
        if key and key in source_links and key not in result:
            result[key] = source_links[key]
        if len(result) >= MAX_ANALYSIS_SOURCES:
            return result

    for key, value in source_links.items():
        if key not in result:
            result[key] = value
        if len(result) >= MAX_ANALYSIS_SOURCES:
            break

    return result


def _collect_reviews_from_scrape_results(
    scrape_results: dict[str, dict | None],
) -> tuple[list, list, dict, list]:
    all_reviews = []
    review_sources = []
    source_review_counts = {}
    scraped_products = []

    for platform, data in scrape_results.items():
        if not data:
            source_review_counts[platform] = 0
            continue

        scraped_products.append(data)
        reviews = data.get("reviews", [])
        source_review_counts[platform] = len(reviews)
        if not reviews:
            continue

        all_reviews.extend(reviews)
        for source in data.get("review_sources") or [platform]:
            if source not in review_sources:
                review_sources.append(source)

    return all_reviews, review_sources, source_review_counts, scraped_products


def _marketplace_from_url(product_url: str) -> str | None:
    host = urlparse(product_url).netloc.lower()
    domain_map = {
        "trendyol.com": "trendyol",
        "hepsiburada.com": "hepsiburada",
        "n11.com": "n11",
        "amazon.com.tr": "amazon",
        "gratis.com": "gratis",
        "watsons.com.tr": "watsons",
        "teknosa.com": "teknosa",
        "mediamarkt.com.tr": "mediamarkt",
        "vatanbilgisayar.com": "vatan",
    }
    for domain, marketplace in domain_map.items():
        if domain in host:
            return marketplace
    return None


def _site_name_from_url(product_url: str) -> str | None:
    marketplace = _marketplace_from_url(product_url)
    if not marketplace:
        return None
    site_names = {
        "n11": "n11",
        "amazon": "Amazon",
        "lcwaikiki": "LC Waikiki",
    }
    return site_names.get(marketplace, marketplace.title())


def _empty_complaint_result() -> dict:
    return {
        "complaints": [],
        "complaint_count": 0,
        "complaint_sources": [],
        "complaint_scope": None,
        "complaint_query": None,
    }


def _empty_price_result() -> dict:
    return {
        "price_history": [],
        "price_sources": [],
        "price_history_source": None,
        "price_history_days": 0,
        "price_history_is_estimated": False,
        "current_market_prices": [],
        "price_search_url": None,
        "price_search_urls": {},
    }
