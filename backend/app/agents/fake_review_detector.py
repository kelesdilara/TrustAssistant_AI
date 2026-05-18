from backend.app.agents.state import AnalysisState


def fake_review_detector_agent(state: AnalysisState) -> AnalysisState:
    reviews = state.get("reviews", [])
    review_count = len(reviews)
    sample_target = state.get("review_sample_target", 1000)
    sample_minimum = state.get("review_sample_minimum", 500)

    repeated_phrases = [
        "kesinlikle tavsiye ederim",
        "cok kaliteli",
        "harika urun",
    ]

    repeated_hits = 0
    for review in reviews:
        comment = _normalize_text(review.get("comment", ""))
        if any(phrase in comment for phrase in repeated_phrases):
            repeated_hits += 1

    repeated_ratio = repeated_hits / review_count if review_count else 0

    if review_count == 0:
        fake_review_score = 0
        review_analysis = (
            "Bu ürün için yorum bulunamadı. Yorum güvenilirliği analizi sınırlı yapılabildi."
        )
    elif repeated_ratio >= 0.35 and repeated_hits >= 10:
        fake_review_score = 75
        review_analysis = (
            f"{review_count} yorum incelendi. Yorumların önemli bir bölümünde benzer olumlu ifadeler tekrar ediyor."
        )
    elif repeated_ratio >= 0.20 and repeated_hits >= 6:
        fake_review_score = 55
        review_analysis = (
            f"{review_count} yorum incelendi. Bazı yorumlarda benzer olumlu ifadeler tekrar ediyor."
        )
    elif repeated_ratio >= 0.10 and repeated_hits >= 4:
        fake_review_score = 30
        review_analysis = (
            f"{review_count} yorum incelendi. Az sayıda benzer ifade var, ancak bu tek başına güçlü bir sahte yorum sinyali değil."
        )
    else:
        fake_review_score = 15
        review_analysis = (
            f"{review_count} yorum incelendi. Yorumlarda belirgin bir tekrar veya sahte yorum sinyali tespit edilmedi."
        )

    if 0 < review_count < sample_minimum:
        review_analysis += (
            f" Hedef {sample_target} yorumdu; {sample_minimum} altinda kaldigi icin sonuc guclu kanit degil."
        )

    state["fake_review_score"] = fake_review_score
    state["review_analysis"] = review_analysis

    return state


def _normalize_text(value: str) -> str:
    value = str(value or "").lower()
    replacements = str.maketrans(
        {
            "ı": "i",
            "ğ": "g",
            "ü": "u",
            "ş": "s",
            "ö": "o",
            "ç": "c",
        }
    )
    return value.translate(replacements)
