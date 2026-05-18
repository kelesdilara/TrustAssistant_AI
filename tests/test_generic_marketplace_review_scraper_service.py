from backend.app.services.generic_marketplace_review_scraper_service import (
    amazon_review_url,
    extract_reviews_from_structured_text,
    is_valid_review_text,
    parse_review_card_text,
)


def test_amazon_review_url_uses_asin():
    url = "https://www.amazon.com.tr/Apple-iPhone-15-128-GB/dp/B0CHX1W1XY"

    assert amazon_review_url(url) == "https://www.amazon.com.tr/product-reviews/B0CHX1W1XY"


def test_parse_review_card_text_prefers_real_comment():
    text = """
    5 yildiz
    Kullanici adi
    Cok guzel bir urun, kargo hizli geldi ve paketleme gayet iyiydi.
    Sepete ekle
    """

    assert parse_review_card_text(text) == "Cok guzel bir urun, kargo hizli geldi ve paketleme gayet iyiydi."


def test_valid_review_text_filters_navigation_copy():
    assert is_valid_review_text("Urun cok kaliteli, fiyat performans olarak memnun kaldim.")
    assert not is_valid_review_text("Sepete ekle favori kampanya urun ozellikleri")


def test_extract_reviews_from_structured_text_reads_json_comments():
    html = '''
    <script>
      {"commentText":"Kokusu guzel ve kalici, paketleme de gayet saglam geldi."}
      {"content":"Sepete ekle favori kampanya urun ozellikleri"}
      {"reviewText":"Memnun kaldim, fiyat performans olarak tavsiye ederim."}
    </script>
    '''

    reviews = extract_reviews_from_structured_text(html, "test", max_reviews=10)

    assert [item["comment"] for item in reviews] == [
        "Kokusu guzel ve kalici, paketleme de gayet saglam geldi.",
        "Memnun kaldim, fiyat performans olarak tavsiye ederim.",
    ]
