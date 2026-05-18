def get_seller_info(
    seller_name: str | None = None,
    product_url: str | None = None,
    complaint_count: int = 0,
) -> dict:
    if not seller_name:
        return {
            "seller_name": None,
            "seller_rating": None,
            "review_count": 0,
            "complaint_count": complaint_count,
            "is_official": False,
        }

    return {
        "seller_name": seller_name,
        "seller_rating": None,
        "review_count": 0,
        "complaint_count": complaint_count,
        "is_official": False,
    }
