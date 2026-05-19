from backend.app.agents.state import AnalysisState


def seller_trust_agent(state: AnalysisState) -> AnalysisState:
    analysis_scope = state.get("analysis_scope")
    seller_name = _real_seller_name(state.get("seller_name"))
    seller_info = state.get("seller_info", {})

    if analysis_scope == "product_name_review_only":
        state["seller_score"] = 70
        state["seller_analysis"] = (
            "Satici analizi yapilmadi; urun adi tek basina hangi saticidan alinacagini gostermez."
        )
        return state

    seller_rating = seller_info.get("seller_rating")       # 10 üzerinden (sayfadan çekildi)
    review_count = seller_info.get("review_count", 0)
    complaint_count = seller_info.get("complaint_count", 0)
    is_official = seller_info.get("is_official", False)
    product_rating = seller_info.get("product_rating")     # 5 üzerinden (sayfadan çekildi)

    seller_score = 55
    reasons = []

    if seller_name:
        seller_score += 10
        reasons.append("Satıcı adı tespit edildi.")
    else:
        reasons.append("Satıcı adı tespit edilemedi.")

    if is_official:
        seller_score += 15
        reasons.append("Satıcı resmi mağaza gibi görünüyor.")

    if isinstance(seller_rating, (int, float)):
        # seller_rating 10 üzerinden
        if seller_rating >= 9:
            seller_score += 20
            reasons.append(f"Satıcı puanı yüksek ({seller_rating}/10).")
        elif seller_rating >= 8:
            seller_score += 12
            reasons.append(f"Satıcı puanı kabul edilebilir ({seller_rating}/10).")
        elif seller_rating >= 7:
            seller_score += 5
            reasons.append(f"Satıcı puanı orta seviyede ({seller_rating}/10).")
        else:
            seller_score -= 10
            reasons.append(f"Satıcı puanı düşük ({seller_rating}/10).")
    else:
        reasons.append("Satıcı puanı alınamadı.")

    # Ürünün kendi yıldız puanı varsa faktöre kat
    if isinstance(product_rating, (int, float)):
        if product_rating >= 4.5:
            seller_score += 10
            reasons.append(f"Ürün müşteri puanı çok yüksek ({product_rating}/5).")
        elif product_rating >= 4.0:
            seller_score += 5
            reasons.append(f"Ürün müşteri puanı iyi ({product_rating}/5).")
        elif product_rating < 3.0:
            seller_score -= 10
            reasons.append(f"Ürün müşteri puanı düşük ({product_rating}/5).")
        else:
            reasons.append(f"Ürün müşteri puanı orta ({product_rating}/5).")

    if review_count >= 1000:
        seller_score += 10
        reasons.append("Satıcı için yüksek sayıda değerlendirme bulunuyor.")
    elif review_count >= 100:
        seller_score += 5
        reasons.append("Satıcı için yeterli sayıda değerlendirme bulunuyor.")
    else:
        seller_score -= 5
        reasons.append("Satıcı değerlendirme sayısı sınırlı görünüyor.")

    if complaint_count >= 20:
        seller_score -= 15
        reasons.append("Satıcı hakkında şikayet yoğunluğu yüksek olabilir.")
    elif complaint_count >= 5:
        seller_score -= 7
        reasons.append("Satıcı hakkında bazı şikayet sinyalleri var.")

    seller_score = max(0, min(100, seller_score))

    state["seller_score"] = seller_score
    state["seller_analysis"] = " ".join(reasons)

    return state


def _real_seller_name(value: str | None) -> str | None:
    if not value:
        return None

    normalized = str(value).lower()
    missing_parts = ["bulunamad", "tespit edilemedi", "bilgisi yok"]
    if any(part in normalized for part in missing_parts):
        return None

    return str(value).strip()
