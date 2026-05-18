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

    # Hepsiburada doğru format:
    # ...-p-HBCV0000XXXX-yorumlari
    if "-p-" in clean_url:
        return f"{clean_url}-yorumlari"

    return clean_url


def scrape_hepsiburada_reviews(
    page: Page,
    product_url: str,
    max_reviews: int = 1000,
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
    print("HEPSIBURADA REVIEW URL:", review_url)

    try:
        page.goto(review_url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(6000)

        page_no = 1
        while len(reviews) < max_reviews:
            print(f"HEPSIBURADA REVIEW PAGE: {page_no}")

            # Sayfadaki lazy içeriklerin oturması için az scroll
            for _ in range(5):
                page.mouse.wheel(0, 1000)
                page.wait_for_timeout(600)

            # 1) Önce varsa JSON içinden yorumları al
            for data in list(captured_jsons):
                for review in extract_reviews_from_any_json(data):
                    add_review_if_valid(reviews, seen, review, max_reviews)
                    if len(reviews) >= max_reviews:
                        return finalize_reviews(reviews, max_reviews)
            captured_jsons.clear()

            # 2) Asıl güvenilir fallback: yorum kartı bazlı DOM okuma
            for review in extract_reviews_from_review_cards(page, max_reviews=max_reviews):
                add_review_if_valid(reviews, seen, review, max_reviews)
                if len(reviews) >= max_reviews:
                    return finalize_reviews(reviews, max_reviews)

            # 3) Yorum kartı selectorları tutmazsa kontrollü body fallback
            if len(reviews) == 0 or page_no == 1:
                for review in extract_reviews_from_body_text(page, max_reviews=60):
                    add_review_if_valid(reviews, seen, review, max_reviews)
                    if len(reviews) >= max_reviews:
                        return finalize_reviews(reviews, max_reviews)

            if len(reviews) >= max_reviews:
                break

            moved = go_to_next_review_page(page, current_page=page_no)
            if not moved:
                break

            page_no += 1
            page.wait_for_timeout(3500)

        return finalize_reviews(reviews, max_reviews)

    except PlaywrightTimeoutError:
        print("HEPSIBURADA REVIEW SCRAPER TIMEOUT")
        return finalize_reviews(reviews, max_reviews)
    except Exception as e:
        print("HEPSIBURADA REVIEW SCRAPER ERROR:", str(e))
        return finalize_reviews(reviews, max_reviews)


def go_to_next_review_page(page: Page, current_page: int) -> bool:
    next_page = current_page + 1

    # Hepsiburada bazen sayfa numarasını button/a olarak basıyor.
    click_candidates = [
        lambda: page.get_by_role("button", name=str(next_page), exact=True),
        lambda: page.get_by_role("link", name=str(next_page), exact=True),
        lambda: page.get_by_text(str(next_page), exact=True),
    ]

    for make_locator in click_candidates:
        try:
            locator = make_locator()
            count = locator.count()
            if count > 0:
                item = locator.last
                item.scroll_into_view_if_needed(timeout=5000)
                page.wait_for_timeout(500)
                item.click(timeout=8000)
                return wait_page_changed(page, next_page)
        except Exception:
            continue

    # Bazı yapılarda "Sonraki" / ok butonu olabilir.
    next_texts = ["Sonraki", "sonraki", "İleri", "ileri", ">"]
    for text in next_texts:
        try:
            locator = page.get_by_text(text, exact=False)
            if locator.count() > 0:
                item = locator.last
                item.scroll_into_view_if_needed(timeout=5000)
                page.wait_for_timeout(500)
                item.click(timeout=8000)
                return wait_page_changed(page, next_page)
        except Exception:
            continue

    # Son çare: URL query parametreleri ile dene.
    base = page.url.split("?")[0]
    for param in ["sayfa", "page", "currentPage"]:
        try:
            page.goto(f"{base}?{param}={next_page}", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3500)
            return True
        except Exception:
            continue

    return False


def wait_page_changed(page: Page, expected_page: int) -> bool:
    try:
        page.wait_for_load_state("domcontentloaded", timeout=15000)
    except Exception:
        pass

    page.wait_for_timeout(2500)

    # Küçük scroll ile yeni sayfa içerikleri gelsin.
    try:
        page.mouse.wheel(0, 700)
        page.wait_for_timeout(1000)
    except Exception:
        pass

    return True


def extract_reviews_from_review_cards(page: Page, max_reviews: int = 1000) -> List[Dict]:
    card_selectors = [
        "[data-test-id*='review']",
        "[data-testid*='review']",
        "[class*='ReviewCard']",
        "[class*='review-card']",
        "[class*='reviewCard']",
        "[class*='Review']",
        "[class*='review']",
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
                text = clean_review_text(raw)
                normalized_card = normalize_review(text)

                if not normalized_card or normalized_card in seen_cards:
                    continue
                seen_cards.add(normalized_card)

                parsed = parse_review_card_text(text)
                if not parsed:
                    continue

                reviews.append(parsed)

                if len(reviews) >= max_reviews:
                    return reviews
            except Exception:
                continue

        if reviews:
            # Bir selector gerçekten kartları bulduysa diğer genel selectorlara geçip çöp üretmeyelim.
            break

    return finalize_reviews(reviews, max_reviews)


def parse_review_card_text(text: str) -> Optional[Dict]:
    original = clean_review_text(text)
    if not original:
        return None

    cleaned = remove_noise(original)
    date = extract_date(cleaned)

    # Kart metninden tarih, kullanıcı, satın aldı, faydalı mı vb. parçaları temizle.
    comment = cleaned
    comment = DATE_RE.sub(" ", comment)
    comment = re.sub(r"\|\s*[^|]{1,80}", " ", comment)
    comment = re.sub(r"[A-ZÇĞİÖŞÜ]{1,3}\s*[A-ZÇĞİÖŞÜ]?\*{2,}.*?(?=Ürün|Paket|Kargo|Çok|Gayet|Güzel|Kaliteli|Memnun|Beğendim|Harika|Mükemmel|Berbat|Kötü|Alınır|Tavsiye|Fiyat|Orijinal|Sağlam|Hızlı|Koli|Islak|Sorun|Teşekkür|$)", " ", comment, flags=re.IGNORECASE)
    comment = re.sub(r"Kullanıcı bu ürünü.*?(?:aldı\.?|$)", " ", comment, flags=re.IGNORECASE)
    comment = re.sub(r"Bu değerlendirme faydalı mı\??.*", " ", comment, flags=re.IGNORECASE)
    comment = re.sub(r"Teşekkür Ederiz\.?|Bildir", " ", comment, flags=re.IGNORECASE)
    comment = re.sub(r"^[A-ZÇĞİÖŞÜ]{1,4}\s*", "", comment).strip()
    comment = fix_turkish_cut_start(comment)
    comment = clean_review_text(comment)

    if not is_valid_review_comment(comment):
        return None

    return {
        "platform": "hepsiburada",
        "rating": extract_rating(original),
        "comment": comment,
        "date": date,
        "username": None,
    }


def extract_reviews_from_body_text(page: Page, max_reviews: int = 60) -> List[Dict]:
    try:
        text = page.inner_text("body")
    except Exception:
        return []

    blocks = re.split(r"(?=\b\d{1,2}\s+(?:" + MONTHS + r"))", text, flags=re.IGNORECASE)
    reviews = []

    for block in blocks:
        parsed = parse_review_card_text(block)
        if parsed:
            reviews.append(parsed)
            if len(reviews) >= max_reviews:
                break

    return reviews


def extract_reviews_from_any_json(data) -> List[Dict]:
    reviews: List[Dict] = []

    def walk(obj):
        if isinstance(obj, dict):
            possible_text_keys = [
                "comment",
                "review",
                "reviewText",
                "commentText",
                "content",
                "text",
                "description",
                "body",
            ]

            for key in possible_text_keys:
                value = obj.get(key)
                if isinstance(value, str):
                    comment = clean_review_text(value)
                    comment = remove_noise(comment)
                    comment = fix_turkish_cut_start(comment)

                    if is_valid_review_comment(comment):
                        reviews.append(
                            {
                                "platform": "hepsiburada",
                                "rating": obj.get("rating") or obj.get("rate") or obj.get("star") or obj.get("stars"),
                                "comment": comment,
                                "date": obj.get("date") or obj.get("createdAt") or obj.get("created_at"),
                                "username": obj.get("userName") or obj.get("username") or obj.get("customerName"),
                            }
                        )

            for value in obj.values():
                walk(value)

        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return reviews


def add_review_if_valid(reviews: List[Dict], seen: set, review: Dict, max_reviews: int) -> None:
    comment = clean_review_text(str(review.get("comment") or ""))
    comment = fix_turkish_cut_start(comment)

    if not is_valid_review_comment(comment):
        return

    normalized = normalize_review(comment)
    if normalized in seen:
        return

    # Aynı yorumun kırpılmış versiyonu geldiyse alma.
    # Örn: "ndirime girdikçe..." yerine daha uzun/tam yorum varsa kısa olanı at.
    for existing in reviews:
        existing_comment = clean_review_text(str(existing.get("comment") or ""))
        existing_norm = normalize_review(existing_comment)

        if is_same_or_cut_duplicate(short_norm=normalized, long_norm=existing_norm):
            return

        # Yeni gelen yorum daha tam/uzunsa eski kırpılmış olanı silip yenisini tut.
        if is_same_or_cut_duplicate(short_norm=existing_norm, long_norm=normalized):
            try:
                reviews.remove(existing)
                seen.discard(existing_norm)
            except ValueError:
                pass
            break

    seen.add(normalized)
    review["comment"] = comment
    reviews.append(review)


def finalize_reviews(reviews: List[Dict], max_reviews: int = 1000) -> List[Dict]:
    """
    Son temizlik:
    - Aynı yorumun kırpılmış/kısa versiyonunu atar.
    - Tam ve uzun olan yorumu bırakır.
    - Aynı normalize metni tekilleştirir.
    """
    cleaned: List[Dict] = []
    seen = set()

    # Uzun yorumları önce işlersek kırpılmış parçalar otomatik elenir.
    sorted_reviews = sorted(
        reviews,
        key=lambda r: len(normalize_review(str(r.get("comment") or ""))),
        reverse=True,
    )

    for review in sorted_reviews:
        comment = fix_turkish_cut_start(clean_review_text(str(review.get("comment") or "")))

        if not is_valid_review_comment(comment):
            continue

        norm = normalize_review(comment)
        if not norm or norm in seen:
            continue

        # Bu yorum, daha önce eklenen daha uzun bir yorumun kırpılmış hali mi?
        if any(is_same_or_cut_duplicate(short_norm=norm, long_norm=normalize_review(str(r.get("comment") or ""))) for r in cleaned):
            continue

        review["comment"] = comment
        cleaned.append(review)
        seen.add(norm)

        if len(cleaned) >= max_reviews:
            break

    # Kullanıcıya daha doğal görünmesi için uzunluk sıralamasını bozup yaklaşık geliş sırasına döndürmek şart değil;
    # analiz için temiz veri daha önemli.
    return cleaned[:max_reviews]


def is_same_or_cut_duplicate(short_norm: str, long_norm: str) -> bool:
    if not short_norm or not long_norm:
        return False

    if short_norm == long_norm:
        return True

    # Çok kısa metinlerde substring agresif olur.
    if len(short_norm) < 28 or len(long_norm) < 28:
        return False

    if len(short_norm) >= len(long_norm):
        return False

    # Direkt içinde geçiyorsa kırpılmış kopyadır.
    if short_norm in long_norm:
        return True

    # İlk harfi/ilk kelimesi kopmuş yorumlar için son kısmı karşılaştır.
    # Örn: "ndirime girdikçe..." ile "indirimde/indirime girdikçe..."
    short_words = short_norm.split()
    long_words = long_norm.split()

    if len(short_words) >= 5:
        tail = " ".join(short_words[-5:])
        if tail and tail in long_norm:
            return True

    # Baştan 1-2 karakter kopmuşsa büyük oranda aynı kabul et.
    if len(short_norm) > 35:
        probe = short_norm[2:]
        if len(probe) > 25 and probe in long_norm:
            return True

    return False


def clean_review_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def remove_noise(text: str) -> str:
    text = clean_review_text(text)
    noise_patterns = [
        r"Kullanıcı bu ürünü.*?(?:aldı\.?|$)",
        r"Bu değerlendirme faydalı mı\??.*",
        r"Teşekkür Ederiz\.?.*",
        r"Bildir$",
        r"Daha Fazla Göster",
        r"Devamını Oku",
        r"Satıcı:.*",
    ]
    for pattern in noise_patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    return clean_review_text(text)


def extract_date(text: str) -> Optional[str]:
    match = DATE_RE.search(text or "")
    return match.group(0) if match else None


def extract_rating(text: str) -> Optional[int]:
    # DOM yıldızları düzgün gelirse yakalamaya çalışır, gelmezse None bırakır.
    match = re.search(r"([1-5])\s*/\s*5", text or "")
    if match:
        return int(match.group(1))
    return None


def fix_turkish_cut_start(comment: str) -> str:
    comment = clean_review_text(comment)

    # Bazı span kırpmalarında ilk harf düşüyor: rün -> Ürün, aketleme -> Paketleme vb.
    fixes = {
        "rün ": "Ürün ",
        "rünü ": "Ürünü ",
        "aketleme ": "Paketleme ",
        "argodan ": "Kargodan ",
        "argo ": "Kargo ",
        "ok ": "Çok ",
        "üzel ": "Güzel ",
        "iyatı ": "Fiyatı ",
        "u değerlendirme": "",
        "ndirime ": "İndirime ",
        "ndirimde ": "İndirimde ",
        "zenli ": "Özenli ",
        "okusunu ": "Kokusunu ",
        "ızlı ": "Hızlı ",
        "sürekli ": "Sürekli ",
        "devamlı ": "Devamlı ",
        "er zaman ": "Her zaman ",
        "ygun ": "Uygun ",
        "aliteli ": "Kaliteli ",
        "esinlikle ": "Kesinlikle ",
        "elen ": "Gelen ",
        "ormal ": "Normal ",
        "ariş ": "Sipariş ",
        "iparişim ": "Siparişim ",
        "epsiburada": "Hepsiburada",
    }

    lower = comment.lower()
    for bad, good in fixes.items():
        if lower.startswith(bad):
            return good + comment[len(bad):]

    return comment


def normalize_review(text: str) -> str:
    text = clean_review_text(text).lower()
    text = re.sub(r"[^\wğüşöçıİĞÜŞÖÇ\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_valid_review_comment(text: str) -> bool:
    if not text:
        return False

    text = clean_review_text(text)
    lower = text.lower()

    hard_blocked = [
        "sepete ekle",
        "satın al",
        "favori",
        "kampanya",
        "ürün özellikleri",
        "soru cevap",
        "soru & cevap",
        "değerlendirmeler",
        "yorumlar",
        "filtrele",
        "sırala",
        "taksit",
        "mağazaya git",
        "kargo bedava",
        "bugün kargoda",
        "tahmini",
        "içinde sipariş",
        "kullanıcı bu ürünü",
        "bu değerlendirme faydalı mı",
        "teşekkür ederiz",
        "bildir",
        "puan",
        "çerez",
        "giriş yap",
        "üye ol",
        "alışveriş kredisi",
        "benzer ürünler",
        "sponsorlu ürün",
    ]

    if any(k in lower for k in hard_blocked):
        return False

    # Sadece tarih / kullanıcı satırı olmasın.
    only_date = DATE_RE.fullmatch(text.strip())
    if only_date:
        return False

    if DATE_RE.search(text) and len(text.split()) <= 7:
        return False

    # Sadece yıldız/sayı olmasın.
    if re.fullmatch(r"[★\s\d\.,]+", text):
        return False

    # Fiyat satırı veya menü satırı olmasın.
    if re.search(r"\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*tl", lower):
        return False

    words = text.split()
    if len(words) < 5:
        return False

    # Gerçek yorum sinyali. Çok katı değil ama çöpleri keser.
    review_keywords = [
        "ürün", "ürünü", "paket", "paketleme", "kargo", "kolide", "koli",
        "güzel", "kaliteli", "memnun", "beğendim", "tavsiye", "harika",
        "mükemmel", "başarılı", "kötü", "beğenmedim", "berbat", "pişman",
        "orijinal", "sağlam", "hızlı", "fiyat", "makul", "uygun", "teşekkür",
        "ıslak", "açık", "kusursuz", "gecikti", "aldım", "alınır",
    ]

    if not any(k in lower for k in review_keywords):
        return False

    return True