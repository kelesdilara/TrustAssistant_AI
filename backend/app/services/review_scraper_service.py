import re
from typing import Dict, List


def extract_reviews_from_page_text(page_text: str, platform: str = "web") -> List[Dict]:
    lines = [
        line.strip()
        for line in page_text.split("\n")
        if 20 <= len(line.strip()) <= 500
    ]

    review_keywords = [
        "beğendim", "memnun", "güzel", "harika", "kaliteli",
        "tavsiye", "kokusu", "kalıcı", "bayıldım", "mükemmel",
        "başarılı", "kötü", "beğenmedim", "pişman", "berbat",
        "akıyor", "yakıyor", "sivilce", "alerji", "kuruttu",
        "nemlendirdi", "paketleme", "orijinal"
    ]

    blocked_keywords = [
        "ürün, kategori veya marka ara",
        "sepete ekle",
        "satın al",
        "favori",
        "tahmini kargoya teslim",
"kargoya teslim",
"gün içinde kargoda",
"kargo bedava",
"teslimat seçenekleri",
        "kampanyalar",
        "ürün özellikleri",
        "soru & cevap",
        "değerlendirmeler",
        "teslimat",
        "iade koşulları",
        "taksit seçenekleri",
        "mağazaya git",
        "satıcı belirlemektedir",
        "trendyol plus",
        "son 24 saatte",
        "kişi görüntüledi",
        "kişi favoriledi",
    ]

    reviews = []
    seen = set()

    for line in lines:
        lower = line.lower()

        if any(blocked in lower for blocked in blocked_keywords):
            continue

        if not any(keyword in lower for keyword in review_keywords):
            continue

        if line in seen:
            continue

        if _looks_like_price_or_menu(line):
            continue

        seen.add(line)

        reviews.append(
            {
                "platform": platform,
                "rating": None,
                "comment": clean_review_text(line),
                "date": None,
                "username": None,
            }
        )

        if len(reviews) >= 30:
            break

    return reviews


def clean_review_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("Daha Fazla Göster", "").strip()
    return text


def _looks_like_price_or_menu(text: str) -> bool:
    lower = text.lower()

    if re.search(r"\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*tl", lower):
        return True

    if len(text.split()) <= 3:
        return True

    return False