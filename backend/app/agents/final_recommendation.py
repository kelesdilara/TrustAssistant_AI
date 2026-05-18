from backend.app.agents.state import AnalysisState
from backend.app.services.ollama_service import ask_ollama
from backend.app.services.scoring_service import (
    calculate_overall_score,
    recommendation_from_score,
)


def final_recommendation_agent(state: AnalysisState) -> AnalysisState:
    analysis_scope = state.get("analysis_scope")
    fake_review_score = state.get("fake_review_score", 50)
    seller_score = state.get("seller_score", 50)
    price_risk_score = state.get("price_risk_score", 50)

    review_only = analysis_scope == "product_name_review_only"
    if review_only:
        overall_score = max(0, min(100, 100 - fake_review_score))
    else:
        overall_score = calculate_overall_score(
            fake_review_score=fake_review_score,
            seller_score=seller_score,
            price_risk_score=price_risk_score,
        )

    product_identifier = (
        state.get("product_name")
        or state.get("product_url")
        or "Girilen urun"
    )

    risk_factors = []

    if fake_review_score >= 70:
        risk_factors.append("Yorumlarda yuksek duzeyde tekrar eden kalip ifadeler var.")
    elif fake_review_score >= 50:
        risk_factors.append(
            "Yorumlarda benzer olumlu ifadeler yogun; bu tek basina sahte yorum gostergesi degildir."
        )

    if not review_only and seller_score < 70:
        risk_factors.append("Satici guven skoru tam guvenli seviyede degil.")
    if not review_only and seller_score < 60:
        risk_factors.append("Satici guven skoru dusuk gorunuyor.")
    elif not review_only and seller_score < 75:
        risk_factors.append("Satici bilgileri sinirli oldugu icin dikkatli incelenmeli.")
    if not review_only and price_risk_score >= 50:
        risk_factors.append("Fiyat veya indirim gercekligi supheli olabilir.")

    scope_note = (
        "Kullanici yalnizca urun adi verdi; ozet sadece yorum sinyallerine dayanmali, "
        "satici veya fiyat hakkinda yorum yapmamali."
        if review_only
        else "Yorum, satici ve fiyat sinyallerini birlikte degerlendir."
    )

    prompt = f"""
Sen Turkce konusan bir alisveris guven analizi asistaniysin.

Kurallar:
- Sadece Turkce yaz.
- Ingilizce kelime kullanma.
- Kullaniciya dogrudan ve sade konus.
- Kesin hukum verme.
- En fazla 5 cumle yaz.
- "Arastirin", "research", "genuine", "product" gibi kelimeler kullanma.
- Skorlari abartmadan acikla.

Urun:
{product_identifier}

Sahte yorum riski:
{fake_review_score}/100

Satici guven skoru:
{seller_score}/100

Fiyat veya indirim risk skoru:
{price_risk_score}/100

Genel guven skoru:
{overall_score}/100

Risk faktorleri:
{risk_factors}

Kapsam notu:
{scope_note}

Kisa bir urun guven ozeti yaz.
"""

    try:
        llm_summary = ask_ollama(prompt)
    except Exception:
        if review_only:
            llm_summary = (
                f"{product_identifier} icin yalnizca yorum sinyalleri analiz edildi; "
                "satici ve fiyat icin link gerekir."
            )
        else:
            llm_summary = (
                f"{product_identifier} icin yorum, satici ve fiyat sinyalleri birlikte analiz edildi."
            )

    state["overall_trust_score"] = overall_score
    state["final_recommendation"] = recommendation_from_score(overall_score)
    state["product_summary"] = llm_summary
    state["risk_factors"] = risk_factors

    return state
