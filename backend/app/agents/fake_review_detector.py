from backend.app.agents.state import AnalysisState


def fake_review_detector_agent(state: AnalysisState) -> AnalysisState:
    reviews = state.get("reviews", [])

    suspicious_patterns = []

    repeated_phrases = [
        "kesinlikle tavsiye ederim",
        "çok kaliteli",
        "harika ürün",
    ]

    suspicious_count = 0

    for review in reviews:
        comment = review.get("comment", "").lower()

        for phrase in repeated_phrases:
            if phrase in comment:
                suspicious_count += 1

    if suspicious_count >= 2:
        suspicious_patterns.append(
            "Yorumlarda tekrar eden olumlu ifadeler bulundu."
        )

    if len(reviews) > 0:
        fake_review_score = min(100, suspicious_count * 20 + 15)
    else:
        fake_review_score = 0

    state["fake_review_score"] = fake_review_score

    state["review_analysis"] = (
        "Yorumlarda bazı tekrar eden ve kısa olumlu ifadeler tespit edildi."
    )

    return state