from backend.app.agents.state import AnalysisState


def price_analysis_agent(state: AnalysisState) -> AnalysisState:
    analysis_scope = state.get("analysis_scope")
    price_history = state.get("price_history", [])
    price_history_source = state.get("price_history_source")
    price_history_days = state.get("price_history_days", 0)
    price_history_is_estimated = state.get("price_history_is_estimated", False)
    current_market_prices = state.get("current_market_prices", [])

    if analysis_scope in {"product_name_review_only", "product_name_with_seller"}:
        state["price_risk_score"] = 50
        state["discount_analysis"] = (
            "Fiyat analizi yapilmadi; urun adi tek basina hangi site, satici veya teklif fiyatinin incelenecegini gostermez."
        )
        return state

    if not price_history:
        state["price_risk_score"] = 70
        state["discount_analysis"] = (
            "Fiyat verisi bulunamadigi icin indirim guvenilirligi sinirli degerlendirildi."
        )
        return state

    prices = [
        item.get("price")
        for item in price_history
        if isinstance(item.get("price"), (int, float))
    ]

    if not prices:
        state["price_risk_score"] = 70
        state["discount_analysis"] = (
            "Fiyat verisi okunamadigi icin indirim guvenilirligi sinirli degerlendirildi."
        )
        return state

    current_price = prices[-1]
    min_price = min(prices)
    avg_price = sum(prices) / len(prices)
    discount_from_avg = ((avg_price - current_price) / avg_price) * 100
    distance_from_min = ((current_price - min_price) / min_price) * 100

    if price_history_source in {"akakce_market_prices", "market_price_sources"}:
        _apply_market_price_analysis(
            state=state,
            current_price=current_price,
            min_price=min_price,
            avg_price=avg_price,
            current_market_prices=current_market_prices,
            price_history_days=price_history_days,
        )
        return state

    _apply_estimated_history_analysis(
        state=state,
        current_price=current_price,
        min_price=min_price,
        discount_from_avg=discount_from_avg,
        distance_from_min=distance_from_min,
        price_history_days=price_history_days,
        price_history_is_estimated=price_history_is_estimated,
    )
    return state


def _apply_market_price_analysis(
    state: AnalysisState,
    current_price: float,
    min_price: float,
    avg_price: float,
    current_market_prices: list,
    price_history_days: int = 0,
) -> None:
    market_count = len(current_market_prices)
    discount_from_avg = ((avg_price - current_price) / avg_price) * 100
    distance_from_min = ((current_price - min_price) / min_price) * 100

    if current_price <= min_price * 1.03:
        price_risk_score = 20
        discount_analysis = (
            f"Fiyat karsilastirma kaynaklarinda {market_count} guncel piyasa fiyati bulundu. "
            "Bu veri gecmis fiyat degil, anlik piyasa karsilastirmasidir. "
            f"Gecmis fiyat gunu: {price_history_days}. "
            "Mevcut fiyat piyasanin en dusuk seviyesine yakin gorunuyor."
        )
    elif current_price <= avg_price:
        price_risk_score = 35
        discount_analysis = (
            f"Fiyat karsilastirma kaynaklarinda {market_count} guncel piyasa fiyati bulundu. "
            "Bu veri gecmis fiyat degil, anlik piyasa karsilastirmasidir. "
            f"Gecmis fiyat gunu: {price_history_days}. "
            f"Mevcut fiyat piyasa ortalamasinin yaklasik %{abs(discount_from_avg):.1f} altinda."
        )
    elif distance_from_min > 20:
        price_risk_score = 65
        discount_analysis = (
            f"Fiyat karsilastirma kaynaklarinda {market_count} guncel piyasa fiyati bulundu. "
            "Bu veri gecmis fiyat degil, anlik piyasa karsilastirmasidir. "
            f"Gecmis fiyat gunu: {price_history_days}. "
            f"Mevcut fiyat en dusuk piyasa fiyatindan yaklasik %{distance_from_min:.1f} daha yuksek."
        )
    else:
        price_risk_score = 50
        discount_analysis = (
            f"Fiyat karsilastirma kaynaklarinda {market_count} guncel piyasa fiyati bulundu. "
            "Bu veri gecmis fiyat degil, anlik piyasa karsilastirmasidir. "
            f"Gecmis fiyat gunu: {price_history_days}. "
            "Mevcut fiyat piyasa araliginda orta seviyede gorunuyor."
        )

    state["price_risk_score"] = round(price_risk_score)
    state["discount_analysis"] = discount_analysis


def _apply_estimated_history_analysis(
    state: AnalysisState,
    current_price: float,
    min_price: float,
    discount_from_avg: float,
    distance_from_min: float,
    price_history_days: int = 90,
    price_history_is_estimated: bool = True,
) -> None:
    history_label = (
        f"tahmini {price_history_days} gunluk seriyle"
        if price_history_is_estimated
        else f"{price_history_days} gunluk fiyat gecmisiyle"
    )
    if current_price <= min_price * 1.03:
        price_risk_score = 20
        discount_analysis = (
            f"Fiyat {history_label} degerlendirildi. "
            f"Mevcut fiyat tahmini ortalamaya gore yaklasik %{discount_from_avg:.1f} daha dusuk."
        )
    elif discount_from_avg >= 15:
        price_risk_score = 35
        discount_analysis = (
            f"Fiyat {history_label} degerlendirildi. "
            f"Mevcut fiyat tahmini ortalamanin yaklasik %{discount_from_avg:.1f} altinda."
        )
    elif distance_from_min > 20:
        price_risk_score = 65
        discount_analysis = (
            f"Fiyat {history_label} degerlendirildi. "
            f"Mevcut fiyat tahmini en dusuk fiyattan yaklasik %{distance_from_min:.1f} daha yuksek."
        )
    else:
        price_risk_score = 50
        discount_analysis = (
            f"Fiyat {history_label} degerlendirildi; fiyat araliginda orta seviye gosteriyor."
        )

    state["price_risk_score"] = round(price_risk_score)
    state["discount_analysis"] = discount_analysis
