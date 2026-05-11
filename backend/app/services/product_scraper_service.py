from urllib.parse import urlparse


def detect_platform(product_url: str | None) -> str:
    if not product_url:
        return "manual"

    domain = urlparse(product_url).netloc.lower()

    if "trendyol" in domain:
        return "trendyol"

    if "hepsiburada" in domain:
        return "hepsiburada"

    if "amazon" in domain:
        return "amazon"

    if "n11" in domain:
        return "n11"

    return "unknown"


def fetch_product_data(
    product_url: str | None,
    product_name: str | None,
    seller_name: str | None,
) -> dict:
    platform = detect_platform(product_url)

    # MVP aşamasında gerçek scraping yerine platform-aware demo veri.
    # Sonraki adımda Playwright burada devreye girecek.
    if product_url:
        return {
            "platform": platform,
            "product_name": product_name or "Linkten alınan ürün",
            "product_url": product_url,
            "seller_name": seller_name or "Linkten alınan satıcı",
            "reviews": [
                {
                    "platform": platform,
                    "rating": 5,
                    "comment": "Ürün kaliteli, ses performansı iyi.",
                    "date": "2026-05-10",
                    "username": "user123",
                },
                {
                    "platform": platform,
                    "rating": 4,
                    "comment": "Kargo hızlı geldi ancak paketleme daha iyi olabilirdi.",
                    "date": "2026-05-09",
                    "username": "user456",
                },
                {
                    "platform": platform,
                    "rating": 2,
                    "comment": "Satıcı iade sürecinde geç cevap verdi.",
                    "date": "2026-05-08",
                    "username": "user789",
                },
            ],
        }

    return {
        "platform": "manual",
        "product_name": product_name,
        "product_url": None,
        "seller_name": seller_name,
        "reviews": [
            {
                "platform": "manual",
                "rating": 5,
                "comment": "Ürün güzel ama yorum sayısı az olduğu için kesin değerlendirme yapılamaz.",
                "date": "2026-05-10",
                "username": "demo_user",
            }
        ],
    }