from backend.app.services import scrape_orchestrator_service as orchestrator


def test_product_name_only_uses_links_for_reviews_without_seller_or_price(monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "search_product_links",
        lambda **_: {
            "trendyol": "https://www.trendyol.com/example-p-1",
            "hepsiburada": "https://www.hepsiburada.com/example-p-HB1",
        },
    )

    def fake_scrape(link, max_reviews_per_source):
        assert max_reviews_per_source == orchestrator.MAX_REVIEWS_PER_SOURCE
        return {
            "product_url": link,
            "product_name": "Example Product",
            "seller_name": "Found Seller",
            "price": "999 TL",
            "reviews": [{"comment": f"yorum {link}", "platform": "test"}],
            "review_sources": ["test"],
        }

    monkeypatch.setattr(orchestrator, "scrape_product_data_sync", fake_scrape)
    monkeypatch.setattr(
        orchestrator,
        "get_complaint_signals",
        lambda **_: (_ for _ in ()).throw(AssertionError("complaints should be skipped")),
    )
    monkeypatch.setattr(
        orchestrator,
        "get_price_signals",
        lambda **_: (_ for _ in ()).throw(AssertionError("price should be skipped")),
    )

    result = orchestrator.collect_all_product_data(product_name="Example Product")

    assert result["analysis_scope"] == "product_name_review_only"
    assert result["product_url"] is None
    assert result["seller_name"] is None
    assert result["price"] is None
    assert result["complaint_count"] == 0
    assert result["price_sources"] == []
    assert result["review_count"] == 2
    assert set(result["source_links"]) == {"trendyol", "hepsiburada"}


def test_product_link_runs_full_analysis_with_large_review_target(monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "search_product_links",
        lambda **_: {
            "gratis": "https://www.gratis.com/linked-product-p-2",
            "watsons": "https://www.watsons.com.tr/linked-product-p-3",
        },
    )

    def fake_scrape(link, max_reviews_per_source):
        assert max_reviews_per_source == orchestrator.MAX_REVIEWS_PER_SOURCE
        return {
            "product_url": link,
            "product_name": "Linked Product",
            "seller_name": "Linked Seller",
            "price": "999 TL",
            "reviews": [{"comment": f"iyi urun {link}", "platform": "test"}],
            "review_count": 1,
            "review_sources": ["test"],
        }

    monkeypatch.setattr(orchestrator, "scrape_product_data_sync", fake_scrape)
    monkeypatch.setattr(orchestrator, "get_complaint_signals", lambda **_: orchestrator._empty_complaint_result())
    monkeypatch.setattr(orchestrator, "get_price_signals", lambda **_: orchestrator._empty_price_result())

    result = orchestrator.collect_all_product_data(
        product_url="https://www.trendyol.com/example-p-1"
    )

    assert result["analysis_scope"] == "product_link_full"
    assert result["product_url"] == "https://www.trendyol.com/example-p-1"
    assert result["seller_name"] == "Linked Seller"
    assert result["price"] == "999 TL"
    assert set(result["source_links"]) == {"trendyol", "gratis", "watsons"}
    assert result["review_count"] == 3
