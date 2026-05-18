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

    seller_rating = seller_info.get("seller_rating")
    review_count = seller_info.get("review_count", 0)
    complaint_count = seller_info.get("complaint_count", 0)
    is_official = seller_info.get("is_official", False)

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
        if seller_rating >= 9:
            seller_score += 20
            reasons.append("Satıcı puanı yüksek görünüyor.")
        elif seller_rating >= 8:
            seller_score += 12
            reasons.append("Satıcı puanı kabul edilebilir seviyede.")
        elif seller_rating >= 7:
            seller_score += 5
            reasons.append("Satıcı puanı orta seviyede.")
        else:
            seller_score -= 10
            reasons.append("Satıcı puanı düşük görünüyor.")
    else:
        reasons.append("Satıcı puanı alınamadı.")

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
