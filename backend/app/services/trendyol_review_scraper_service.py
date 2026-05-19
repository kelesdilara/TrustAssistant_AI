import re
from typing import Dict, List
from urllib.parse import urlparse

from playwright.sync_api import Page

from backend.app.services.generic_marketplace_review_scraper_service import (
    extract_reviews_from_structured_text,
)


def build_trendyol_review_url(product_url: str) -> str:
    clean_url = product_url.split("?")[0].rstrip("/")

    if "/yorumlar" in clean_url:
        return clean_url

    return f"{clean_url}/yorumlar"


def scrape_trendyol_reviews(page: Page, product_url: str, max_reviews: int = 80) -> List[Dict]:
    review_url = build_trendyol_review_url(product_url)
    print(f"TRENDYOL REVIEW URL: {review_url}")

    try:
        page.goto(review_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        print(f"TRENDYOL PAGE TITLE: {page.title()}")

        reviews: List[Dict] = []
        seen = set()

        for review in _collect_reviews_from_api(page, product_url, max_reviews):
            _add_review(reviews, seen, review, max_reviews)
            if len(reviews) >= max_reviews:
                return reviews[:max_reviews]

        idle_rounds = 0
        last_count = 0

        for _ in range(50):
            _collect_visible_reviews(page, reviews, seen, max_reviews)
            if len(reviews) >= max_reviews:
                return reviews[:max_reviews]

            if len(reviews) == last_count:
                idle_rounds += 1
            else:
                idle_rounds = 0
                last_count = len(reviews)

            if idle_rounds >= 8:
                break

            page.mouse.wheel(0, 1400)
            page.wait_for_timeout(400)

        if not reviews:
            body_text = page.inner_text("body")
            page_html = page.content()
            fallback_reviews = (
                extract_reviews_from_structured_text(page_html, "trendyol", max_reviews)
                or extract_reviews_from_text(body_text, max_reviews=max_reviews)
            )
            for review in fallback_reviews:
                _add_review(reviews, seen, review, max_reviews)

        print(f"TRENDYOL REVIEWS FOUND: {len(reviews)}")
        return reviews[:max_reviews]

    except Exception as e:
        print(f"TRENDYOL ERROR: {e}")
        return []


def _collect_visible_reviews(
    page: Page,
    reviews: List[Dict],
    seen: set,
    max_reviews: int,
) -> None:
    selectors = [
        ".comment-text",
        ".review-comment",
        ".comment",
        ".reviews .comment",
        "[class*='comment-text']",
        "[class*='review'] [class*='comment']",
        "[class*='Comment']",
    ]

    for selector in selectors:
        try:
            elements = page.query_selector_all(selector)
        except Exception:
            continue

        for element in elements:
            try:
                text = clean_review_text(element.inner_text())

                if not is_valid_review(text):
                    continue

                if text in seen:
                    continue

                seen.add(text)
                reviews.append(
                    {
                        "platform": "trendyol",
                        "rating": None,
                        "comment": text,
                        "date": None,
                        "username": None,
                    }
                )

                if len(reviews) >= max_reviews:
                    return

            except Exception:
                continue


def _collect_reviews_from_api(
    page: Page,
    product_url: str,
    max_reviews: int,
) -> List[Dict]:
    product_id = _extract_product_id(product_url)
    if not product_id:
        return []

    merchant_id = _extract_merchant_id(product_url)
    merchant_suffix = f"&merchantId={merchant_id}" if merchant_id else ""

    candidates = [
        f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/reviews/{product_id}?page={{page}}&size=30{merchant_suffix}",
        f"https://public-mdc.trendyol.com/discovery-web-socialgw-service/reviews/{product_id}?page={{page}}&size=30",
        f"https://public.trendyol.com/discovery-web-socialgw-service/reviews/{product_id}?page={{page}}&size=30{merchant_suffix}",
    ]
    reviews: List[Dict] = []
    seen = set()

    for template in candidates:
        for page_no in range(0, max(1, (max_reviews // 30) + 2)):
            url = template.format(page=page_no)
            try:
                response = page.request.get(
                    url,
                    headers={
                        "accept": "application/json, text/plain, */*",
                        "referer": product_url,
                    },
                    timeout=12000,
                )
                if not response.ok:
                    if page_no == 0:
                        break
                    continue
                payload = response.json()
            except Exception:
                if page_no == 0:
                    break
                continue

            batch = _extract_reviews_from_json(payload)
            before = len(reviews)
            for review in batch:
                _add_review(reviews, seen, review, max_reviews)
                if len(reviews) >= max_reviews:
                    return reviews

            if len(reviews) == before:
                break

        if reviews:
            break

    return reviews


def _extract_reviews_from_json(payload) -> List[Dict]:
    reviews: List[Dict] = []

    def visit(value):
        if isinstance(value, dict):
            text = (
                value.get("comment")
                or value.get("commentText")
                or value.get("reviewText")
                or value.get("text")
                or value.get("content")
            )
            if isinstance(text, str) and is_valid_review(text):
                reviews.append(
                    {
                        "platform": "trendyol",
                        "rating": value.get("rate") or value.get("rating"),
                        "comment": clean_review_text(text),
                        "date": value.get("commentDate") or value.get("date"),
                        "username": value.get("userFullName") or value.get("userName"),
                    }
                )
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return reviews


def _extract_product_id(product_url: str) -> str | None:
    path = urlparse(product_url).path
    match = re.search(r"-p-(\d+)", path)
    if match:
        return match.group(1)
    return None


def _extract_merchant_id(product_url: str) -> str | None:
    match = re.search(r"merchantId=(\d+)", product_url)
    return match.group(1) if match else None


def _add_review(
    reviews: List[Dict],
    seen: set,
    review: Dict,
    max_reviews: int,
) -> None:
    comment = clean_review_text(review.get("comment", ""))
    key = _normalize_text(comment)
    if not key or key in seen or not is_valid_review(comment):
        return
    seen.add(key)
    review["comment"] = comment
    reviews.append(review)


def extract_reviews_from_text(page_text: str, max_reviews: int = 30) -> List[Dict]:
    lines = [
        clean_review_text(line)
        for line in page_text.split("\n")
        if 20 <= len(line.strip()) <= 500
    ]

    reviews = []
    seen = set()

    for line in lines:
        if not is_valid_review(line):
            continue

        if line in seen:
            continue

        seen.add(line)
        reviews.append(
            {
                "platform": "trendyol",
                "rating": None,
                "comment": line,
                "date": None,
                "username": None,
            }
        )

        if len(reviews) >= max_reviews:
            break

    return reviews


def clean_review_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("Daha Fazla Göster", "").strip()
    text = text.replace("Devamını Oku", "").strip()
    return text


def is_valid_review(text: str) -> bool:
    if not text:
        return False

    lower = _normalize_text(text)

    blocked_keywords = [
        "urun kategori veya marka ara",
        "sepete ekle",
        "satin al",
        "favori",
        "kampanya",
        "urun ozellikleri",
        "soru cevap",
        "degerlendirmeler",
        "teslimat",
        "iade",
        "taksit",
        "magazaya git",
        "satici",
        "trendyol plus",
        "son 24 saatte",
        "kisi goruntuledi",
        "kisi favoriledi",
        "tahmini kargoya teslim",
        "kargoya teslim",
        "gun icinde kargoda",
        "kargo bedava",
        "yorumlar",
        "puan",
        "filtrele",
        "sirala",
    ]

    review_keywords = [
        "begendim",
        "memnun",
        "guzel",
        "harika",
        "kaliteli",
        "tavsiye",
        "kokusu",
        "kalici",
        "bayildim",
        "mukemmel",
        "basarili",
        "kotu",
        "begenmedim",
        "pisman",
        "berbat",
        "akiyor",
        "yakiyor",
        "sivilce",
        "alerji",
        "kuruttu",
        "nemlendirdi",
        "paketleme",
        "orijinal",
        "alinir",
        "almayin",
        "ise yaradi",
        "etkili",
        "hizli",
        "kargo",
        "fiyat",
        "performans",
    ]

    if any(keyword in lower for keyword in blocked_keywords):
        return False

    if not any(keyword in lower for keyword in review_keywords):
        return False

    if re.search(r"\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*tl", lower):
        return False

    if len(text.split()) < 4:
        return False

    return True


def _normalize_text(value: str) -> str:
    value = str(value or "").lower()
    replacements = str.maketrans(
        {
            "ı": "i",
            "ğ": "g",
            "ü": "u",
            "ş": "s",
            "ö": "o",
            "ç": "c",
        }
    )
    value = value.translate(replacements)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())
