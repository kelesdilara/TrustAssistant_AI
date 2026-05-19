import json
import re
from typing import Dict, List, Optional

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)
from backend.app.services.browser_factory import launch_stealth_browser, new_stealth_page
from backend.app.services.review_orchestrator_service import collect_reviews_from_sources


def scrape_product_data_sync(product_url: str, max_reviews_per_source: int = 80) -> Dict:
    lower_url = product_url.lower()
    needs_visible_browser = _needs_visible_browser(lower_url)

    with sync_playwright() as p:
        browser = launch_stealth_browser(p, headless=not needs_visible_browser)
        page = new_stealth_page(browser)

        try:
            page.goto(product_url, wait_until="domcontentloaded", timeout=30000)

            if needs_visible_browser:
                page.wait_for_timeout(4000)
                page.mouse.move(300, 400)
                page.wait_for_timeout(500)
                page.mouse.wheel(0, 500)
                page.wait_for_timeout(1000)
            else:
                page.wait_for_timeout(2000)

            json_ld_data = _extract_json_ld(page)

            product_name = (
                _get_first_text(
                    page,
                    [
                        "h1",
                        "[data-test-id='title']",
                        "[data-testid='product-name']",
                        ".product-name",
                        ".product-title",
                        "#product-name",
                        ".pr-new-br",
                        ".product_title",
                        ".product-detail-name",
                        ".pdp-title",
                        "[class*='ProductTitle']",
                        "[class*='productTitle']",
                    ],
                )
                or _get_meta_content(page, "meta[property='og:title']")
                or json_ld_data.get("name")
                or page.title()
            )

            price = (
                _get_first_text(
                    page,
                    [
                        "[data-test-id='price-current-price']",
                        "[data-testid='price']",
                        ".price",
                        ".product-price",
                        ".current-price",
                        ".a-price",
                        ".prc-dsc",
                        "[class*='price']",
                        "[class*='Price']",
                    ],
                )
                or _extract_price_from_text(page.inner_text("body"))
                or str(json_ld_data.get("price", ""))
            )

            seller_name = (
                _get_first_text(
                    page,
                    [
                        "[data-test-id='merchant-name']",
                        "[data-testid='seller-name']",
                        "[data-test-id='seller-name']",
                        ".seller-name",
                        ".merchant-name",
                        "[class*='sellerName']",
                        "[class*='SellerName']",
                        "[class*='seller-name']",
                        "[class*='merchantName']",
                        "span[class*='seller']",
                        "a[class*='seller']",
                    ],
                )
                or json_ld_data.get("seller")
            )

            # Satıcı puanı (10 üzerinden — Hepsiburada, Trendyol vb.)
            seller_rating_text = _get_first_text(
                page,
                [
                    "[data-test-id='seller-score']",
                    "[data-test-id='merchant-score']",
                    "[class*='sellerScore']",
                    "[class*='SellerScore']",
                    "[class*='seller-score']",
                    "[class*='merchantScore']",
                    "[class*='MerchantScore']",
                ],
            )
            seller_rating = _parse_seller_rating(seller_rating_text)

            # Ürün yıldız puanı (5 üzerinden)
            product_rating_text = _get_first_text(
                page,
                [
                    "[data-test-id='product-rating']",
                    "[data-testid='product-rating']",
                    "[class*='productRating']",
                    "[class*='ProductRating']",
                    "[class*='rating-score']",
                    "[class*='ratingScore']",
                    "[class*='StarRating']",
                    "[itemprop='ratingValue']",
                ],
            )
            product_rating = _parse_product_rating(product_rating_text)

            security_blocked = _is_security_page(product_name, page)

            if security_blocked:
                product_name = _extract_product_name_from_url(product_url)
                seller_name = _seller_name_for_blocked_page(product_url) or seller_name
                price = None

            review_result = collect_reviews_from_sources(
                page=page,
                product_url=product_url,
                product_name=product_name,
                max_reviews_per_source=max_reviews_per_source,
            )

            reviews = review_result.get("reviews", [])
            review_sources = review_result.get("review_sources", [])

            return {
                "success": True,
                "source": "security_blocked_partial" if security_blocked else "live",
                "product_url": product_url,
                "product_name": _clean_text(product_name) or "Ürün adı bulunamadı",
                "seller_name": _clean_text(seller_name) or None,
                "seller_rating": seller_rating,
                "product_rating": product_rating,
                "price": _clean_text(price) or None,
                "reviews": reviews,
                "review_count": len(reviews),
                "review_sources": review_sources,
            }
            # --- Düzeltilen Kısım Sonu ---

        except PlaywrightTimeoutError:
            return {
                "success": False,
                "error": "Sayfa zaman aşımına uğradı.",
                "product_url": product_url,
                "reviews": [],
                "review_count": 0,
                "review_sources": [],
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "product_url": product_url,
                "reviews": [],
                "review_count": 0,
                "review_sources": [],
            }

        finally:
            browser.close()


def _is_security_page(product_name, page) -> bool:
    title = str(product_name or "").lower()

    if "güvenlik" in title or "security" in title:
        return True

    try:
        body = page.inner_text("body").lower()
        security_words = [
            "güvenlik kontrolü",
            "security check",
            "robot olmadığınızı",
            "captcha",
        ]
        return any(word in body for word in security_words)
    except Exception:
        return False


def _needs_visible_browser(lower_url: str) -> bool:
    visible_domains = []
    return any(domain in lower_url for domain in visible_domains)


def _parse_seller_rating(text: str | None) -> float | None:
    """Satıcı puanını float olarak çıkar (10 üzerinden → 10 üzerinden döner)."""
    if not text:
        return None
    numbers = re.findall(r"\d+[.,]?\d*", text.replace(",", "."))
    for n in numbers:
        try:
            v = float(n)
            if 0 < v <= 10:
                return round(v, 1)
        except ValueError:
            continue
    return None


def _parse_product_rating(text: str | None) -> float | None:
    """Ürün yıldız puanını float olarak çıkar (5 üzerinden)."""
    if not text:
        return None
    numbers = re.findall(r"\d+[.,]?\d*", text.replace(",", "."))
    for n in numbers:
        try:
            v = float(n)
            if 0 < v <= 5:
                return round(v, 1)
        except ValueError:
            continue
    return None


def _seller_name_for_blocked_page(product_url: str) -> Optional[str]:
    lower = product_url.lower()
    if "hepsiburada.com" in lower:
        return "Hepsiburada"
    if "amazon.com.tr" in lower:
        return "Amazon"
    return None


def _get_first_text(page, selectors: List[str]) -> Optional[str]:
    for selector in selectors:
        try:
            element = page.query_selector(selector)
            if element:
                text = element.inner_text().strip()
                if text:
                    return text
        except Exception:
            continue
    return None


def _get_meta_content(page, selector: str) -> Optional[str]:
    try:
        element = page.query_selector(selector)
        if element:
            return element.get_attribute("content")
    except Exception:
        pass
    return None


def _extract_json_ld(page) -> Dict:
    try:
        scripts = page.query_selector_all("script[type='application/ld+json']")

        for script in scripts:
            raw = script.inner_text()
            try:
                data = json.loads(raw)
            except Exception:
                continue

            items = data if isinstance(data, list) else [data]

            for item in items:
                if not isinstance(item, dict):
                    continue

                if item.get("@type") in ["Product", "ProductGroup"]:
                    offers = item.get("offers", {})
                    seller = ""
                    price = ""

                    if isinstance(offers, dict):
                        price = offers.get("price", "")
                        seller_data = offers.get("seller", {})
                        if isinstance(seller_data, dict):
                            seller = seller_data.get("name", "")

                    return {
                        "name": item.get("name", ""),
                        "price": price,
                        "seller": seller,
                    }
    except Exception:
        pass

    return {}


def _extract_price_from_text(text: str) -> Optional[str]:
    matches = re.findall(r"\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*TL", text)
    if matches:
        return matches[0]
    return None


def _extract_product_name_from_url(url: str) -> str:
    try:
        clean = url.split("?")[0].split("#")[0]
        slug = clean.split("/")[-1]
        if "-p-" in slug:
            slug = slug.split("-p-")[0]
        elif "-pm-" in slug:
            slug = slug.split("-pm-")[0]
        slug = slug.replace("-", " ")
        return slug.title()
    except Exception:
        return "Ürün"


def _clean_text(value) -> str:
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text
