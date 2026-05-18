from backend.app.services.price_history_service import (
    _clean_seller_name,
    build_history_from_market_prices,
    extract_market_prices_from_text,
    filter_market_prices_by_current_price,
    merge_market_prices,
    parse_price_to_float,
)


def test_parse_price_to_float_handles_turkish_price_text():
    assert parse_price_to_float("49.499,00 TL") == 49499.0
    assert parse_price_to_float("1.234 TL") == 1234.0
    assert parse_price_to_float("Son 10 Gunun En Dusuk Fiyati! 49.999 TL 49.299 TL") == 49299.0


def test_extract_market_prices_from_text_collects_akakce_like_prices():
    text = """
    Seller A
    49.499,00 TL
    Kargo bedava
    Seller B
    50.199,90 TL
    """

    prices = extract_market_prices_from_text(text)

    assert [item["price"] for item in prices] == [49499.0, 50199.9]
    assert prices[0]["source"] == "akakce"


def test_build_history_from_market_prices_marks_akakce_sources():
    history = build_history_from_market_prices(
        market_prices=[
            {"price": 100.0},
            {"price": 120.0},
        ],
        current_price=110.0,
    )

    assert len(history) == 3
    assert history[0]["source"] == "market_price_high"
    assert history[-1]["price"] == 110.0


def test_filter_market_prices_by_current_price_removes_unrelated_prices():
    prices = [
        {"price": 9224.0},
        {"price": 47699.0},
        {"price": 95000.0},
    ]

    assert filter_market_prices_by_current_price(prices, current_price=49299.0) == [
        {"price": 47699.0}
    ]


def test_merge_market_prices_keeps_sources_and_sorts():
    prices = merge_market_prices(
        [{"source": "akakce", "seller": "A", "price": 100.0}],
        [{"source": "cimri", "seller": "B", "price": 95.0}],
    )

    assert [item["source"] for item in prices] == ["cimri", "akakce"]
    assert [item["price"] for item in prices] == [95.0, 100.0]


def test_clean_seller_name_removes_variant_noise():
    assert _clean_seller_name("Mavi") is None
    assert _clean_seller_name("Sarı") is None
    assert _clean_seller_name("Mağazaya Git") is None
    assert _clean_seller_name("Alarm Kur") is None
    assert _clean_seller_name("512 GB") is None
    assert _clean_seller_name("Example Store") == "Example Store"
