from backend.app.services.complaint_scraper_service import (
    _build_queries,
    _filter_relevant_complaints,
    extract_complaints_from_cards,
    extract_complaints_from_text,
)


def test_extract_complaints_from_text_keeps_complaint_like_lines():
    text = """
    Sikayetvar ana sayfa
    Siparisim teslim edilmedi ve para iadesi konusunda kimseye ulasamiyorum.
    Marka karsilastir ve cozum merkezi
    Urun arizali geldi, servis sureci cozulmedi ve magdur oldum.
    """

    complaints = extract_complaints_from_text(text, max_complaints=5)

    assert len(complaints) == 2
    assert complaints[0]["source"] == "sikayetvar"


def test_extract_complaints_from_cards_keeps_title_and_url():
    cards = [
        {
            "title": "Trendyol teslim edilmeyen siparis icin para iadesi yapmiyor",
            "href": "/trendyol/trendyol-teslim-edilmeyen-siparis",
        },
        {
            "title": "Giris yap",
            "href": "/giris",
        },
    ]

    complaints = extract_complaints_from_cards(cards, max_complaints=5)

    assert complaints == [
        {
            "source": "sikayetvar",
            "title": "Trendyol teslim edilmeyen siparis icin para iadesi yapmiyor",
            "url": "https://www.sikayetvar.com/trendyol/trendyol-teslim-edilmeyen-siparis",
        }
    ]


def test_filter_relevant_complaints_removes_unrelated_titles():
    complaints = [
        {
            "source": "sikayetvar",
            "title": "Migros Yemek siparisimin gecikmesi",
            "url": "https://www.sikayetvar.com/migros-yemek/gecikme",
        },
        {
            "source": "sikayetvar",
            "title": "Gurgencler teslim edilmeyen iPhone siparisi",
            "url": "https://www.sikayetvar.com/gurgencler/teslim-edilmeyen-iphone",
        },
    ]

    relevant = _filter_relevant_complaints(
        complaints,
        query="Gürgençler Apple Yetkili Satıcı",
    )

    assert [item["title"] for item in relevant] == [
        "Gurgencler teslim edilmeyen iPhone siparisi"
    ]


def test_build_queries_tries_seller_then_product():
    assert _build_queries("Example Seller", "Example Product") == [
        ("Example Seller", "seller"),
        ("Example Product", "product"),
    ]


def test_build_queries_tries_site_between_seller_and_product():
    assert _build_queries("Example Seller", "Example Product", site_name="Gratis") == [
        ("Example Seller", "seller"),
        ("Gratis", "site"),
        ("Example Product", "product"),
    ]
