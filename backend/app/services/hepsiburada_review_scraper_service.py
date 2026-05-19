import re
from typing import Dict, List, Optional

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError


MONTHS = (
    "Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|Haziran|Temmuz|Ağustos|Agustos|"
    "Eylül|Eylul|Ekim|Kasım|Kasim|Aralık|Aralik"
)
DATE_RE = re.compile(
    rf"\b\d{{1,2}}\s+(?:{MONTHS})(?:\s+\d{{4}})?(?:,\s*\w+)?\b",
    re.IGNORECASE,
)


def build_hepsiburada_review_url(product_url: str) -> str:
    clean_url = product_url.split("?")[0].split("#")[0].rstrip("/")

    if clean_url.endswith("-yorumlari") or "/yorumlari" in clean_url:
        return clean_url

    # Sadece standart -p- formatına -yorumlari ekle
    # -pm- formatı için ürün sayfası kullanılır (security bypass)
    if "-p-" in clean_url and "-pm-" not in clean_url:
        return f"{clean_url}-yorumlari"

    return clean_url


def scrape_hepsiburada_reviews(
    page: Page,
    product_url: str,
    max_reviews: int = 50,
) -> List[Dict]:
    reviews: List[Dict] = []
    seen = set()
    captured_jsons = []

    def handle_response(response):
        try:
            url = response.url.lower()
            content_type = response.headers.get("content-type", "").lower()
            if "application/json" not in content_type:
                return
            if any(k in url for k in ["review", "comment", "yorum", "degerlendirme", "değerlendirme"]):
                captured_jsons.append(response.json())
        except Exception:
            pass

    page.on("response", handle_response)
    review_url = build_hepsiburada_review_url(product_url)
    print(f"HEPSIBURADA REVIEW URL: {review_url}")

    try:
        page.goto(review_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        page_title = page.title()
        print(f"HEPSIBURADA PAGE TITLE: {page_title}")

        if "güvenlik" in page_title.lower() or "security" in page_title.lower():
            print("HEPSIBURADA SECURITY BLOCK — skipping")
            return []

        # Yorumlar sekmesine tıkla
        for tab_selector in [
            "[data-test-id='reviews-tab']",
            "[data-test-id='review-tab']",
            "a[href*='yorum']",
            "button:has-text('Yorumlar')",
            "a:has-text('Yorumlar')",
        ]:
            try:
                el = page.query_selector(tab_selector)
                if el:
                    el.scroll_into_view_if_needed()
                    el.click()
                    page.wait_for_timeout(1500)
                    break
            except Exception:
                continue

        # Scroll ile lazy yorumları yükle
        for _ in range(5):
            page.mouse.wheel(0, 1200)
            page.wait_for_timeout(400)

        # JSON API'den yakala
        for data in list(captured_jsons):
            for review in extract_reviews_from_any_json(data):
                add_review_if_valid(reviews, seen, review, max_reviews)
                if len(reviews) >= max_reviews:
                    return finalize_reviews(reviews, max_reviews)
        captured_jsons.clear()

        # DOM'dan kart bazlı çek
        if len(reviews) < max_reviews:
            for review in extract_reviews_from_review_cards(page, max_reviews=max_reviews):
                add_review_if_valid(reviews, seen, review, max_reviews)

        # Body text fallback
        if not reviews:
            for review in extract_reviews_from_body_text(page, max_reviews=max_reviews):
                add_review_if_valid(reviews, seen, review, max_reviews)

        print(f"HEPSIBURADA REVIEWS FOUND: {len(reviews)}")
        return finalize_reviews(reviews, max_reviews)

    except PlaywrightTimeoutError:
        print("HEPSIBURADA TIMEOUT")
        return finalize_reviews(reviews, max_reviews)
    except Exception as e:
        print(f"HEPSIBURADA ERROR: {e}")
        return finalize_reviews(reviews, max_reviews)


def extract_reviews_from_review_cards(page: Page, max_reviews: int = 50) -> List[Dict]:
    card_selectors = [
        "[data-test-id*='review']",
        "[data-testid*='review']",
        "[class*='ReviewCard']",
        "[class*='review-card']",
        "[class*='reviewCard']",
        "[class*='Comment']",
        "[class*='comment']",
    ]
    reviews: List[Dict] = []
    seen_cards = set()

    for selector in card_selectors:
        try:
            elements = page.query_selector_all(selector)
        except Exception:
            continue
        for element in elements:
            try:
                raw = element.inner_text()
                text = _clean(raw)
                norm = _normalize(text)
                if not norm or norm in seen_cards:
                    continue
                seen_cards.add(norm)
                parsed = _parse_card(text)
                if parsed:
                    reviews.append(parsed)
                if len(reviews) >= max_reviews:
                    return reviews
            except Exception:
                continue
        if reviews:
            break

    return finalize_reviews(reviews, max_reviews)


def extract_reviews_from_body_text(page: Page, max_reviews: int = 50) -> List[Dict]:
    try:
        text = page.inner_text("body")
    except Exception:
        return []
    blocks = re.split(r"(?=\b\d{1,2}\s+(?:" + MONTHS + r"))", text, flags=re.IGNORECASE)
    reviews = []
    for block in blocks:
        parsed = _parse_card(block)
        if parsed:
            reviews.append(parsed)
        if len(reviews) >= max_reviews:
            break
    return reviews


def extract_reviews_from_any_json(data) -> List[Dict]:
    reviews: List[Dict] = []

    def walk(obj):
        if isinstance(obj, dict):
            for key in ["comment", "review", "reviewText", "commentText", "content", "text", "body"]:
                value = obj.get(key)
                if isinstance(value, str) and len(value.strip()) >= 10:
                    reviews.append({
                        "platform": "hepsiburada",
                        "rating": _coerce_rating(
                            obj.get("rating") or obj.get("rate") or obj.get("star")
                        ),
                        "comment": value.strip(),
                        "date": obj.get("date") or obj.get("createdAt"),
                        "username": obj.get("userName") or obj.get("username"),
                    })
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return reviews


def add_review_if_valid(reviews: List[Dict], seen: set, review: Dict, max_reviews: int) -> None:
    comment = _clean(str(review.get("comment") or ""))
    if len(comment.split()) < 5:
        return
    norm = _normalize(comment)
    if norm in seen:
        return
    seen.add(norm)
    review["comment"] = comment
    reviews.append(review)


def finalize_reviews(reviews: List[Dict], max_reviews: int) -> List[Dict]:
    return reviews[:max_reviews]


def _parse_card(text: str) -> Optional[Dict]:
    text = _clean(text)
    if len(text.split()) < 5:
        return None
    noise = ["sepete ekle", "satın al", "favorilere", "kampanya", "filtrele", "giriş yap"]
    if any(n in text.lower() for n in noise):
        return None
    return {
        "platform": "hepsiburada",
        "rating": _extract_rating(text),
        "comment": text[:500],
        "date": _extract_date(text),
        "username": None,
    }


def _extract_rating(text: str) -> Optional[int]:
    match = re.search(r"([1-5])\s*/\s*5", text or "")
    return int(match.group(1)) if match else None


def _extract_date(text: str) -> Optional[str]:
    match = DATE_RE.search(text or "")
    return match.group(0) if match else None


def _coerce_rating(value) -> Optional[int]:
    try:
        f = float(value)
        return round(f) if 1 <= f <= 5 else None
    except (TypeError, ValueError):
        return None


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = text.replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


def _normalize(text: str) -> str:
    text = _clean(text).lower()
    text = re.sub(r"[^\wğüşöçıİĞÜŞÖÇ\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()
