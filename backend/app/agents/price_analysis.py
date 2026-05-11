from backend.app.agents.state import AnalysisState


def price_analysis_agent(state: AnalysisState) -> AnalysisState:
    product_name = state.get("product_name")
    product_url = state.get("product_url")

    if product_url:
        price_risk_score = 60
        discount_analysis = (
            "Ürün linki üzerinden fiyat/indirim analizi yapılacak şekilde hazırlandı. "
            "Şimdilik demo veriye göre indirim gerçekliği orta riskli görünüyor."
        )
    elif product_name:
        price_risk_score = 65
        discount_analysis = (
            "Sadece ürün adı girildiği için fiyat geçmişi kesin doğrulanamadı. "
            "Bu nedenle indirim güvenilirliği sınırlı değerlendirildi."
        )
    else:
        price_risk_score = 75
        discount_analysis = (
            "Ürün bilgisi eksik olduğu için fiyat analizi yüksek belirsizlikle yapıldı."
        )

    state["price_risk_score"] = price_risk_score
    state["discount_analysis"] = discount_analysis

    return state