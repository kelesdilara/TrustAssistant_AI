KNOWN_BRANDS = {
    # Teknoloji
    "apple", "samsung", "huawei", "xiaomi", "oppo", "sony", "lg", "philips",
    "bosch", "siemens", "arçelik", "beko", "vestel", "casper", "lenovo",
    "asus", "dell", "hp", "acer", "msi", "toshiba", "panasonic", "canon",
    "nikon", "dyson", "braun", "tefal", "rowenta", "karcher", "lego",
    # Moda / Giyim
    "nike", "adidas", "puma", "reebok", "new balance", "converse", "vans",
    "levi's", "tommy hilfiger", "lacoste", "polo", "zara", "h&m", "mango",
    "koton", "lcw", "lc waikiki", "defacto", "trendyolmilla",
    # Kozmetik / Sağlık
    "loreal", "l'oreal", "nivea", "dove", "garnier", "maybelline", "mac",
    "clinique", "estee lauder", "neutrogena", "avene", "vichy",
    # Marketplace resmi mağazaları
    "hepsiburada", "trendyol", "amazon", "n11", "gittigidiyor",
    "teknosa", "mediamarkt", "vatan", "bimeks",
}

OFFICIAL_STORE_KEYWORDS = {
    "resmi", "official", "store", "mağaza", "türkiye", "turkey",
    "authorized", "yetkili", "distribütör",
}


def get_seller_info(
    seller_name: str | None = None,
    product_url: str | None = None,
    complaint_count: int = 0,
    seller_rating: float | None = None,
    product_rating: float | None = None,
) -> dict:
    if not seller_name:
        return {
            "seller_name": None,
            "seller_rating": None,
            "review_count": 0,
            "complaint_count": complaint_count,
            "is_official": False,
            "product_rating": product_rating,
        }

    is_official = _is_official_seller(seller_name)

    # Gerçek satıcı puanı yoksa tahmin et
    resolved_rating = seller_rating
    resolved_review_count = 500 if is_official else 0

    return {
        "seller_name": seller_name,
        "seller_rating": resolved_rating,
        "review_count": resolved_review_count,
        "complaint_count": complaint_count,
        "is_official": is_official,
        "product_rating": product_rating,
    }


def _is_official_seller(seller_name: str) -> bool:
    normalized = seller_name.lower().strip()

    for brand in KNOWN_BRANDS:
        if brand in normalized:
            return True

    for keyword in OFFICIAL_STORE_KEYWORDS:
        if keyword in normalized:
            return True

    return False
