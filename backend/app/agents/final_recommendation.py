from backend.app.agents.state import AnalysisState
from backend.app.services.ollama_service import ask_ollama
from backend.app.services.scoring_service import (
    calculate_overall_score,
    recommendation_from_score,
)


def final_recommendation_agent(state: AnalysisState) -> AnalysisState:
    fake_review_score = state.get("fake_review_score", 50)
    seller_score = state.get("seller_score", 50)
    price_risk_score = state.get("price_risk_score", 50)

    overall_score = calculate_overall_score(
        fake_review_score=fake_review_score,
        seller_score=seller_score,
        price_risk_score=price_risk_score,
    )

    product_identifier = (
        state.get("product_name")
        or state.get("product_url")
        or "Girilen ürün"
    )

    risk_factors = []

    if fake_review_score >= 50:
        risk_factors.append("Yorumlarda sahte/tekrarlı ifade riski var.")

    if seller_score < 70:
        risk_factors.append("Satıcı güven skoru tam güvenli seviyede değil.")

    if price_risk_score >= 50:
        risk_factors.append("Fiyat veya indirim gerçekliği şüpheli olabilir.")

    prompt = f"""
Sen Türkçe konuşan bir alışveriş güven analizi asistanısın.

Kurallar:
- Sadece Türkçe yaz.
- İngilizce kelime kullanma.
- Kullanıcıya doğrudan ve sade konuş.
- Kesin hüküm verme.
- En fazla 5 cümle yaz.
- "Araştırın", "research", "genuine", "product" gibi kelimeler kullanma.
- Skorları abartmadan açıkla.

Ürün:
{product_identifier}

Sahte yorum riski:
{fake_review_score}/100

Satıcı güven skoru:
{seller_score}/100

Fiyat veya indirim risk skoru:
{price_risk_score}/100

Genel güven skoru:
{overall_score}/100

Risk faktörleri:
{risk_factors}

Kısa bir ürün güven özeti yaz.
"""

    try:
        llm_summary = ask_ollama(prompt)
    except Exception:
        llm_summary = (
            f"{product_identifier} için yorum, satıcı ve fiyat sinyalleri birlikte analiz edildi."
        )

    state["overall_trust_score"] = overall_score
    state["final_recommendation"] = recommendation_from_score(overall_score)
    state["product_summary"] = llm_summary
    state["risk_factors"] = risk_factors

    return state