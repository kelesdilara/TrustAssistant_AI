from backend.app.services.marketplace_search_service import (
    _extract_hepsiburada_product_link,
    _extract_marketplace_product_link,
    _extract_trendyol_product_link,
)


def test_extract_hepsiburada_link_from_escaped_json_payload():
    html = r'''
        <script>
            {"productUrl":"\/apple-iphone-15-128-gb-p-HBCV00004X7ABC?magaza=Example"}
        </script>
    '''

    link = _extract_hepsiburada_product_link(
        html=html,
        base_url="https://www.hepsiburada.com/ara?q=iphone+15",
        product_name="Apple iPhone 15 128 GB",
    )

    assert link == "https://www.hepsiburada.com/apple-iphone-15-128-gb-p-HBCV00004X7ABC"


def test_extract_hepsiburada_link_prefers_product_name_match():
    html = """
        <a href="/samsung-galaxy-s24-kilif-p-HBCV0000KILIF">KILIF</a>
        <a href="/samsung-galaxy-s24-256-gb-p-HBCV0000PHONE">PHONE</a>
    """

    link = _extract_hepsiburada_product_link(
        html=html,
        base_url="https://www.hepsiburada.com/ara?q=samsung+galaxy+s24",
        product_name="Samsung Galaxy S24 256 GB",
    )

    assert link == "https://www.hepsiburada.com/samsung-galaxy-s24-256-gb-p-HBCV0000PHONE"


def test_extract_trendyol_link_still_finds_product_links():
    html = """
        <a href="/apple-iphone-15-128-gb-p-123456789?boutiqueId=1">PHONE</a>
    """

    link = _extract_trendyol_product_link(
        html=html,
        base_url="https://www.trendyol.com/sr?q=iphone+15",
        product_name="Apple iPhone 15 128 GB",
    )

    assert link == "https://www.trendyol.com/apple-iphone-15-128-gb-p-123456789"


def test_extract_new_marketplace_links_from_common_patterns():
    cases = [
        (
            "n11",
            '<a href="/urun/apple-iphone-15-128-gb-555666777">iphone</a>',
            "https://www.n11.com/urun/apple-iphone-15-128-gb-555666777",
        ),
        (
            "amazon",
            '<a href="/Apple-iPhone-15-128-GB/dp/B0CHX1W1XY">iphone</a>',
            "https://www.amazon.com.tr/Apple-iPhone-15-128-GB/dp/B0CHX1W1XY",
        ),
        (
            "teknosa",
            '<a href="/apple-iphone-15-128gb-akilli-telefon-p-125078965">iphone</a>',
            "https://www.teknosa.com/apple-iphone-15-128gb-akilli-telefon-p-125078965",
        ),
        (
            "vatan",
            '<a href="/iphone-15-128-gb-akilli-telefon.html">iphone</a>',
            "https://www.vatanbilgisayar.com/iphone-15-128-gb-akilli-telefon.html",
        ),
    ]

    for marketplace, html, expected in cases:
        link = _extract_marketplace_product_link(
            marketplace=marketplace,
            html=html,
            base_url=f"https://www.example.com/search?q=iphone",
            product_name="iphone 15",
        )

        assert link == expected
