import re

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
        or "Girilen ürün"
    )
    seller_name = state.get("seller_name") or "Bilinmiyor"
    review_count = state.get("review_count", 0)
    discount_analysis = state.get("discount_analysis", "")

    risk_factors = []
    if fake_review_score >= 70:
        risk_factors.append("Yorumlarda yüksek düzeyde tekrar eden kalıp ifadeler var.")
    elif fake_review_score >= 50:
        risk_factors.append("Yorumlarda benzer olumlu ifadeler yoğun.")
    if not review_only and seller_score < 60:
        risk_factors.append("Satıcı güven skoru düşük görünüyor.")
    elif not review_only and seller_score < 75:
        risk_factors.append("Satıcı bilgileri sınırlı, dikkatli incelenmeli.")
    if not review_only and price_risk_score >= 60:
        risk_factors.append("Fiyat veya indirim gerçekliği şüpheli olabilir.")

    TURKISH_RULE = (
        "ZORUNLU KURAL: Yanıtında tek bir İngilizce kelime bile KULLANAMAZSIN. "
        "'product', 'very', 'positive', 'parent', 'genuine', 'research', 'store', 'market' "
        "gibi İngilizce kelimeler yasaktır. Sadece ve sadece Türkçe yaz.\n\n"
    )

    prompt = TURKISH_RULE + _build_prompt(
        analysis_scope=analysis_scope,
        product_identifier=product_identifier,
        seller_name=seller_name,
        review_count=review_count,
        fake_review_score=fake_review_score,
        seller_score=seller_score,
        price_risk_score=price_risk_score,
        overall_score=overall_score,
        discount_analysis=discount_analysis,
        review_sources=state.get("review_sources", []),
        source_review_counts=state.get("source_review_counts", {}),
    )

    try:
        llm_summary = ask_ollama(prompt)
        if _llm_output_invalid(llm_summary):
            llm_summary = _fallback_summary(
                analysis_scope=analysis_scope,
                product_identifier=product_identifier,
                seller_name=state.get("seller_name", ""),
                overall_score=overall_score,
                seller_score=seller_score,
            )
    except Exception:
        llm_summary = _fallback_summary(
            analysis_scope=analysis_scope,
            product_identifier=product_identifier,
            seller_name=seller_name,
            overall_score=overall_score,
            seller_score=seller_score,
        )

    state["overall_trust_score"] = overall_score
    state["final_recommendation"] = recommendation_from_score(overall_score)
    state["product_summary"] = llm_summary
    state["risk_factors"] = risk_factors

    return state


def _build_prompt(
    analysis_scope,
    product_identifier,
    seller_name,
    review_count,
    fake_review_score,
    seller_score,
    price_risk_score,
    overall_score,
    discount_analysis,
    review_sources,
    source_review_counts,
) -> str:

    sources_text = ""
    if source_review_counts:
        parts = [f"{k}: {v} yorum" for k, v in source_review_counts.items() if v > 0]
        if parts:
            sources_text = ", ".join(parts)

    # URL ile link verildi — tam analiz
    if analysis_scope == "product_link_full":
        seller_verdict = (
            "güvenilir görünüyor" if seller_score >= 70
            else "dikkatli olunmalı" if seller_score >= 50
            else "şüpheli, başka satıcı önerilir"
        )
        price_verdict = (
            "uygun görünüyor" if price_risk_score <= 35
            else "orta seviyede" if price_risk_score <= 55
            else "şişirilmiş olabilir"
        )
        review_verdict = (
            "temiz, sahte yorum sinyali düşük" if fake_review_score <= 25
            else "bazı tekrar eden ifadeler mevcut" if fake_review_score <= 55
            else "yüksek tekrar, dikkat edilmeli"
        )
        return f"""
Sen Türkçe konuşan bir alışveriş güven asistanısın.

Görevin: Kullanıcının attığı ürün linkini analiz edip kısa, net, aksiyonlu bir değerlendirme yazmak.

Veriler:
- Ürün: {product_identifier}
- Satıcı: {seller_name}
- İncelenen yorum sayısı: {review_count} ({sources_text or 'kaynak belirtilmedi'})
- Yorum güvenilirliği: {review_verdict} (skor: {fake_review_score}/100)
- Satıcı güveni: {seller_verdict} (skor: {seller_score}/100)
- Fiyat değerlendirmesi: {price_verdict} — {discount_analysis}
- Genel güven skoru: {overall_score}/100

Kurallar:
- Sadece Türkçe yaz
- En fazla 5 cümle
- Şu 3 konuyu mutlaka değerlendir: ürün yorumları, satıcı güveni, fiyat uygunluğu
- Satıcı güven skoru 60'ın altındaysa "bu satıcı yerine başka bir satıcıdan alın" öner
- Fiyat şişirilmişse "daha uygun fiyat için karşılaştırın" öner
- Kesin hüküm verme, ama net ve anlaşılır ol
"""

    # Ürün adı verildi + satıcı var
    elif analysis_scope == "product_name_with_seller":
        return f"""
Sen Türkçe konuşan bir alışveriş güven asistanısın.

Görevin: Kullanıcının sorgusunu analiz edip ürün hakkında kısa bir değerlendirme yapmak.

Veriler:
- Ürün/Sorgu: {product_identifier}
- Satıcı: {seller_name}
- İncelenen yorum sayısı: {review_count} ({sources_text or 'çeşitli kaynaklar'})
- Yorum güvenilirliği skoru: {fake_review_score}/100 (düşük = daha güvenilir)
- Satıcı güven skoru: {seller_score}/100
- Genel güven skoru: {overall_score}/100

Kurallar:
- Sadece Türkçe yaz
- En fazla 5 cümle
- Ürünün genel algısını yorumlara dayanarak özetle
- Satıcı güvenilirse bunu belirt, değilse daha güvenilir bir satıcı aramasını öner
- Kesin hüküm verme
"""

    # Sadece ürün adı — yorum bazlı analiz
    else:
        trusted_sources = [s for s in (review_sources or []) if s in {
            "trendyol", "hepsiburada", "amazon", "n11", "teknosa",
            "mediamarkt", "vatan", "ebebek", "lcwaikiki", "gratis", "watsons"
        }]
        sources_list = ", ".join(trusted_sources) if trusted_sources else "çeşitli siteler"
        return f"""
Sen Türkçe konuşan bir alışveriş güven asistanısın.

Görevin: Kullanıcının araştırdığı ürün hakkında kısa, yönlendirici bir değerlendirme yapmak.

Veriler:
- Ürün: {product_identifier}
- İncelenen yorum sayısı: {review_count} ({sources_text or sources_list})
- Yorum güvenilirliği skoru: {fake_review_score}/100 (düşük = daha güvenilir)
- Genel güven skoru: {overall_score}/100
- Yorumların toplandığı siteler: {sources_list}

Kurallar:
- Sadece Türkçe yaz
- En fazla 5 cümle
- Yorumlara göre ürünün genel kalitesini değerlendir
- Ürün iyiyse güvenle alınabilecek siteleri belirt ({sources_list})
- Ürün kötüyse veya yorumlar şüpheliyse uyar
- Kesin hüküm verme
"""


def _llm_output_invalid(text: str) -> bool:
    """LLM çıktısı geçersizse True döner (yabancı dil, İngilizce, boş vb.)."""
    if not text or len(text.strip()) < 20:
        return True
    # Arapça, İbranice, Çince, Japonca vb. Unicode blokları
    if re.search(r"[؀-ۿ֐-׿一-鿿぀-ヿ]", text):
        return True
    # Yaygın İngilizce kelimeler
    english_words = [
        "product", "very", "positive", "parent", "genuine",
        "store", "market", "review", "overall", "seller",
    ]
    lower = text.lower()
    if sum(1 for w in english_words if w in lower) >= 2:
        return True
    return False


def _fallback_summary(
    analysis_scope,
    product_identifier,
    seller_name,
    overall_score,
    seller_score,
) -> str:
    if analysis_scope == "product_link_full":
        if overall_score >= 70:
            return (
                f"{product_identifier} için yapılan analiz olumlu sonuç verdi. "
                f"Satıcı ({seller_name}) güvenilir görünüyor ve fiyat makul düzeyde. "
                "Gönül rahatlığıyla satın alabilirsiniz."
            )
        elif overall_score >= 50:
            return (
                f"{product_identifier} için orta düzey güven skoru elde edildi. "
                f"Satıcı ({seller_name}) hakkında dikkatli olunması önerilir. "
                "Satın almadan önce satıcı yorumlarını incelemeniz tavsiye edilir."
            )
        else:
            return (
                f"{product_identifier} için düşük güven skoru elde edildi. "
                f"Satıcı ({seller_name}) şüpheli görünüyor. "
                "Bu satıcı yerine ürünü Trendyol veya Hepsiburada gibi güvenilir bir platformdan almanız önerilir."
            )
    else:
        if overall_score >= 70:
            return (
                f"{product_identifier} hakkındaki yorumlar genel olarak olumlu. "
                "Trendyol, Hepsiburada veya Amazon gibi güvenilir sitelerden alabilirsiniz."
            )
        else:
            return (
                f"{product_identifier} hakkındaki yorumlar karışık sinyal veriyor. "
                "Satın almadan önce birden fazla kaynaktan araştırmanız önerilir."
            )
