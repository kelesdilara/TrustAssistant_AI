import html
import json
import re
from typing import Dict, List
from urllib.parse import urlparse

from playwright.sync_api import Page


COMMON_REVIEW_CARD_SELECTORS = [
    "[data-test-id*='review']",
    "[data-testid*='review']",
    "[class*='Review']",
    "[class*='review']",
    "[class*='Comment']",
    "[class*='comment']",
    "[class*='Yorum']",
    "[class*='yorum']",
    ".comment-text",
    ".review-comment",
    ".review-text",
    ".user-comment",
    ".customer-review",
]

COMMON_REVIEW_TEXT_SELECTORS = [
    "[data-test-id*='comment']",
    "[data-testid*='comment']",
    "[class*='comment-text']",
    "[class*='review-text']",
    "[class*='reviewText']",
    "[class*='ReviewText']",
    "[class*='user-comment']",
    "[class*='customer-review']",
]

BLOCKED_TEXT_PARTS = [
    "sepete ekle",
    "satın al",
    "satin al",
    "favori",
    "kampanya",
    "ürün özellikleri",
    "urun ozellikleri",
    "soru cevap",
    "değerlendirmeler",
    "degerlendirmeler",
    "teslimat",
    "iade",
    "taksit",
    "mağazaya git",
    "magazaya git",
    "satıcı",
    "satici",
    "filtrele",
    "sırala",
    "sirala",
    "çerez",
    "cerez",
    "gizlilik",
    "kvkk",
    "üye girişi",
    "uye girisi",
    "alışveriş yapmak için",
    "alisveris yapmak icin",
    "n11 depom",
    "hızlıca kargoya verilir",
    "hizlica kargoya verilir",
    "takip et",
    "mağaza puanı",
    "magaza puani",
    "ücretsiz kargo",
    "ucretsiz kargo",
    "sipariş verirsen",
    "siparis verirsen",
    "içerisinde sipariş",
    "icerisinde siparis",
    "tahmini kargoya",
    "fiyat ve özellik",
    "fiyat ve ozellik",
    "hemen inceleyin",
    "hızlıca sahip olun",
    "hizlica sahip olun",
    "renk seçenekleri",
    "renk secenekleri",
    "modellerinde",
    "bionic çip",
    "bionic cip",
]

REVIEW_HINTS = [
    "beğendim",
    "begendim",
    "memnun",
    "güzel",
    "guzel",
    "harika",
    "kaliteli",
    "tavsiye",
    "kokusu",
    "kalıcı",
    "kalici",
    "mükemmel",
    "mukemmel",
    "başarılı",
    "basarili",
    "kötü",
    "kotu",
    "beğenmedim",
    "begenmedim",
    "pişman",
    "pisman",
    "berbat",
    "paketleme",
    "orijinal",
    "alınır",
    "alinir",
    "almayın",
    "almayin",
    "hızlı",
    "hizli",
    "kargo",
    "fiyat",
    "performans",
    "rahat",
    "yumuşak",
    "yumusak",
    "beden",
    "rengi",
    "görsel",
    "gorsel",
    "tam oldu",
    "sağlam",
    "saglam",
]


def scrape_generic_marketplace_reviews(
    page: Page,
    product_url: str,
    platform: str,
    max_reviews: int = 80,
    review_url_candidates: list[str] | None = None,
    extra_card_selectors: list[str] | None = None,
    extra_text_selectors: list[str] | None = None,
) -> List[Dict]:
    reviews: List[Dict] = []
    seen = set()

    for review_url in _unique_urls(review_url_candidates or [product_url]):
        try:
            page.goto(review_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            idle_rounds = 0
            last_count = 0
            for _ in range(160):
                page.mouse.wheel(0, 1100)
                page.wait_for_timeout(400)

                for review in _extract_reviews_from_selectors(
                    page=page,
                    platform=platform,
                    max_reviews=max_reviews,
                    extra_card_selectors=extra_card_selectors or [],
                    extra_text_selectors=extra_text_selectors or [],
                ):
                    _add_review(reviews, seen, review, max_reviews)
                    if len(reviews) >= max_reviews:
                        return reviews

                if len(reviews) == last_count:
                    idle_rounds += 1
                else:
                    idle_rounds = 0
                    last_count = len(reviews)

                if reviews and idle_rounds >= 12:
                    break

            if not reviews:
                body_text = page.inner_text("body")
                page_html = page.content()
                fallback_reviews = (
                    extract_reviews_from_structured_text(page_html, platform, max_reviews)
                    or _extract_reviews_from_text(body_text, platform, max_reviews=max_reviews)
                )
                for review in fallback_reviews:
                    _add_review(reviews, seen, review, max_reviews)
                    if len(reviews) >= max_reviews:
                        return reviews

        except Exception as exc:
            print(f"{platform.upper()} REVIEW SCRAPER ERROR [{review_url}]: {exc}")
            continue

        if len(reviews) >= max_reviews:
            break

    return reviews[:max_reviews]


def _extract_reviews_from_selectors(
    page: Page,
    platform: str,
    max_reviews: int,
    extra_card_selectors: list[str],
    extra_text_selectors: list[str],
) -> List[Dict]:
    reviews: List[Dict] = []

    for selector in extra_text_selectors + COMMON_REVIEW_TEXT_SELECTORS:
        try:
            elements = page.query_selector_all(selector)
        except Exception:
            continue

        for element in elements:
            try:
                text = clean_review_text(element.inner_text())
            except Exception:
                continue

            if is_valid_review_text(text):
                reviews.append(_review(platform, text))
                if len(reviews) >= max_reviews:
                    return reviews

    for selector in extra_card_selectors + COMMON_REVIEW_CARD_SELECTORS:
        try:
            elements = page.query_selector_all(selector)
        except Exception:
            continue

        for element in elements:
            try:
                text = clean_review_text(element.inner_text())
            except Exception:
                continue

            parsed = parse_review_card_text(text)
            if parsed and is_valid_review_text(parsed):
                reviews.append(_review(platform, parsed))
                if len(reviews) >= max_reviews:
                    return reviews

    return reviews


def _extract_reviews_from_text(page_text: str, platform: str, max_reviews: int) -> List[Dict]:
    lines = [
        clean_review_text(line)
        for line in page_text.split("\n")
        if 20 <= len(line.strip()) <= 500
    ]

    reviews = []
    for line in lines:
        if is_valid_review_text(line):
            reviews.append(_review(platform, line))
            if len(reviews) >= max_reviews:
                break

    return reviews


def extract_reviews_from_structured_text(
    page_text: str,
    platform: str,
    max_reviews: int,
) -> List[Dict]:
    reviews: List[Dict] = []
    seen = set()
    text = html.unescape(str(page_text or ""))

    key_pattern = (
        r'"(?:comment|commentText|reviewText|review_text|review|content|text|message)"'
        r'\s*:\s*("(?:(?:\\.)|[^"\\])*")'
    )
    for match in re.finditer(key_pattern, text, flags=re.IGNORECASE):
        try:
            candidate = json.loads(match.group(1))
        except Exception:
            candidate = match.group(1).strip('"')

        candidate = clean_review_text(candidate)
        key = _normalize_text(candidate)
        if key in seen or not is_valid_review_text(candidate):
            continue

        seen.add(key)
        reviews.append(_review(platform, candidate))
        if len(reviews) >= max_reviews:
            return reviews

    return reviews


def parse_review_card_text(text: str) -> str:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    candidates = [
        clean_review_text(line)
        for line in lines
        if 20 <= len(line.strip()) <= 500
    ]

    for candidate in sorted(candidates, key=len, reverse=True):
        if is_valid_review_text(candidate):
            return candidate

    return clean_review_text(text) if is_valid_review_text(text) else ""


def clean_review_text(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    text = text.replace("Devamını Oku", "").replace("Daha Fazla Göster", "").strip()
    return text


def is_valid_review_text(text: str) -> bool:
    if not text:
        return False

    normalized = _normalize_text(text)
    if len(normalized.split()) < 4:
        return False

    if any(blocked in normalized for blocked in BLOCKED_TEXT_PARTS):
        return False

    if re.search(r"\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*tl", normalized):
        return False

    return any(hint in normalized for hint in REVIEW_HINTS)


def review_url_with_path(product_url: str, path: str) -> str:
    clean_url = product_url.split("?")[0].split("#")[0].rstrip("/")
    return f"{clean_url}{path}"


def amazon_review_url(product_url: str) -> str:
    clean_url = product_url.split("?")[0].split("#")[0]
    match = re.search(r"/(?:dp|product)/([A-Z0-9]{10})", clean_url)
    if not match:
        match = re.search(r"/([A-Z0-9]{10})(?:/|$)", clean_url)
    if not match:
        return review_url_with_path(product_url, "/#customerReviews")

    asin = match.group(1)
    parsed = urlparse(clean_url)
    return f"{parsed.scheme}://{parsed.netloc}/product-reviews/{asin}"


def _review(platform: str, text: str) -> Dict:
    return {
        "platform": platform,
        "rating": None,
        "comment": text,
        "date": None,
        "username": None,
    }


def _add_review(reviews: List[Dict], seen: set, review: Dict, max_reviews: int) -> None:
    comment = clean_review_text(review.get("comment", ""))
    key = _normalize_text(comment)

    if not key or key in seen or len(reviews) >= max_reviews:
        return

    seen.add(key)
    review["comment"] = comment
    reviews.append(review)


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
    return " ".join(value.split())


def _unique_urls(urls: list[str]) -> list[str]:
    seen = set()
    result = []

    for url in urls:
        if not url or url in seen:
            continue
        seen.add(url)
        result.append(url)

    return result
